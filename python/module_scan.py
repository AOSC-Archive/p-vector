import os
from pathlib import PosixPath

import json
import sqlite3
import logging
import binascii
import functools
import collections
import concurrent.futures
from subprocess import CalledProcessError

import module_ipc
import internal_db
import internal_pkgscan
import internal_dpkg_version

logging.basicConfig(
    format='%(asctime)s %(levelname).1s [%(name)5.5s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)

logger_scan = logging.getLogger('SCAN')

FILETYPES = {
    0o100000: 'reg',
    0o120000: 'lnk',
    0o140000: 'sock',
    0o020000: 'chr',
    0o060000: 'blk',
    0o040000: 'dir',
    0o010000: 'fifo',
}

def split_soname(s: str):
    spl = s.rsplit('.so', 1)
    if len(spl) == 1:
        return s, ''
    else:
        return spl[0]+'.so', spl[1]

def scan_deb(fullpath: str, filename: str, size: int, mtime: int):
    # Scan it.
    try:
        p = internal_pkgscan.scan(fullpath)
    except CalledProcessError as e:
        if e.returncode in (1, 2):
            logger_scan.error('%s is corrupted, status: %d', fullpath, e.returncode)
            return
        raise
    # Make a new document
    pkginfo = {
        'package': p.control['Package'],
        'version': p.control['Version'],
        'architecture': p.control['Architecture'],
        'filename': filename,
        'size': size,
        'sha256': binascii.b2a_hex(bytes(p.p['hash_value'])),
        'mtime': mtime,
        'debtime': p.p['time'],
        'control': json.dumps(collections.OrderedDict(p.control),
            separators=(',', ':'))
    }
    sodeps = []
    for row in p.p['so_provides']:
        sodeps.append((0,) + split_soname(row))
    for row in p.p['so_depends']:
        sodeps.append((1,) + split_soname(row))
    files = []
    for row in p.p['files']:
        path, name = os.path.split(os.path.normpath(
            os.path.join('/', row['path'])))
        files.append((
            path.lstrip('/'), name, row['size'],
            FILETYPES.get(row['type'], str(row['type'])),
            row['perm'], row['uid'], row['gid'], row['uname'], row['gname']
        ))
    return pkginfo, sodeps, files

dpkg_vercomp_key = functools.cmp_to_key(
    internal_dpkg_version.dpkg_version_compare)

def scan_dir(db: sqlite3.Connection, base_dir: str, branch: str, component: str):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() + 1)
    pool_path = PosixPath(base_dir).joinpath('pool')
    search_path = pool_path.joinpath(branch).joinpath(component)
    compname = '%s-%s' % (branch, component)
    cur = db.cursor()
    cur.execute(
        "SELECT package, version, repo, architecture, filename, size, mtime "
        "FROM dpkg_packages WHERE filename LIKE ?",
        (os.path.join('pool', branch, component) + '/',))
    dup_pkgs = set()
    ignore_files = set()
    del_list = []
    for package, version, repo, architecture, filename, size, mtime in cur:
        fullpath = PosixPath(base_dir).joinpath(filename)
        if fullpath.is_file():
            stat = fullpath.stat()
            if size == stat.st_size and mtime == int(stat.st_mtime):
                ignore_files.add(str(fullpath))
            else:
                #dup_pkgs[filename] = (package, version, architecture)
                dup_pkgs.add(filename)
        else:
            del_list.append((filename, package, version, repo))
            logger_scan.info('CLEAN  %s', filename)
            module_ipc.publish_change(
                compname, package, architecture, 'delete', version, '')
    for row in del_list:
        cur.execute("DELETE FROM dpkg_package_sodep "
            "WHERE package=? AND version=? AND repo=?", row[1:])
        cur.execute("DELETE FROM dpkg_package_files "
            "WHERE package=? AND version=? AND repo=?", row[1:])
        cur.execute("DELETE FROM dpkg_packages WHERE filename=?", (row[0],))
    check_list = [[] for _ in range(4)]
    for fullpath in search_path.rglob('*.deb'):
        if not fullpath.is_file():
            continue
        stat = fullpath.stat()
        sfullpath = str(fullpath)
        if sfullpath in ignore_files:
            ignore_files.remove(sfullpath)
            continue
        check_list[0].append(sfullpath)
        check_list[1].append(str(fullpath.relative_to(base_dir)))
        check_list[2].append(stat.st_size)
        check_list[3].append(int(stat.st_mtime))
        #check_list.append((sfullpath, str(fullpath.relative_to(base_dir)),
        #    stat.st_size, int(stat.st_mtime)))
    with executor:
        for pkginfo, sodeps, files in executor.map(scan_deb, *check_list):
            arch = pkginfo['architecture']
            if arch == 'all':
                arch = 'noarch'
            repo = '%s/%s' % (arch, branch)
            if component != 'main':
                repo = component + '-' + repo
            pkginfo['repo'] = repo
            dbkey = (pkginfo['package'], pkginfo['version'], repo)
            if pkginfo['filename'] in dup_pkgs:
                logger_scan.info('UPDATE %s', pkginfo['filename'])
                module_ipc.publish_change(
                    compname, pkginfo['package'], pkginfo['architecture'],
                    'overwrite', pkginfo['version'], pkginfo['version']
                )
            else:
                cur.execute("SELECT version, filename FROM dpkg_packages "
                    "WHERE package=? AND repo=?", (pkginfo['package'], repo))
                results = cur.fetchall()
                if results:
                    oldver = max(results, key=lambda x: dpkg_vercomp_key(x[0]))
                    vercomp = internal_dpkg_version.dpkg_version_compare(
                        oldver[0], pkginfo['version'])
                    if vercomp == -1:
                        logger_scan.info('NEWER  %s %s %s >> %s',
                            pkginfo['architecture'], pkginfo['package'],
                            pkginfo['version'], oldver[0])
                        module_ipc.publish_change(
                            compname, pkginfo['package'], pkginfo['architecture'],
                            'upgrade', oldver[0], pkginfo['version']
                        )
                    elif vercomp:
                        logger_scan.warning('OLD    %s %s %s',
                            pkginfo['architecture'], pkginfo['package'],
                            pkginfo['version'])
                    else:
                        cur.execute("DELETE FROM dpkg_package_sodep "
                            "WHERE package=? AND version=? AND repo=?", dbkey)
                        cur.execute("DELETE FROM dpkg_package_files "
                            "WHERE package=? AND version=? AND repo=?", dbkey)
                        cur.execute("DELETE FROM dpkg_packages "
                            "WHERE package=? AND version=? AND repo=?", dbkey)
                        logger_scan.error('DUP    %s == %s',
                            oldver[1], pkginfo['filename'])
                else:
                    logger_scan.info('NEW    %s %s %s', pkginfo['architecture'],
                        pkginfo['package'], pkginfo['version'])
                    module_ipc.publish_change(
                        compname, pkginfo['package'], pkginfo['architecture'],
                        'new', '', pkginfo['version']
                    )
            keys, qms, vals = internal_db.make_insert(pkginfo)
            cur.execute("INSERT INTO dpkg_packages (%s) VALUES (%s)" %
                (keys, qms), vals)
            for row in sodeps:
                cur.execute("INSERT INTO dpkg_package_sodep VALUES "
                    "(?,?,?,?,?,?)", dbkey + row)
            for row in files:
                cur.execute("INSERT INTO dpkg_package_files VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?)", dbkey + row)

def scan(db: sqlite3.Connection, base_dir: str):
    pool_dir = base_dir + '/pool'
    internal_db.init_db(db)
    for i in PosixPath(pool_dir).iterdir():
        if not i.is_dir():
            continue
        branch_name = i.name
        print('====', branch_name, '====')
        for j in PosixPath(pool_dir).joinpath(branch_name).iterdir():
            if not j.is_dir():
                continue
            component_name = j.name
            scan_dir(db, base_dir, branch_name, component_name)
            logger_scan.info('==== %s-%s ====', branch_name, component_name)
