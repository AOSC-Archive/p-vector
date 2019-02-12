import os
import json
import gzip
import shutil
import sqlite3
import logging
import datetime
import subprocess
from pathlib import PosixPath, PurePath

import deb822
from internal_pkgscan import sha256_file

logger_rel = logging.getLogger('REL')

def generate(db: sqlite3.Connection, base_dir: str,
             conf_common: dict, conf_branches: dict):
    dist_dir = base_dir + '/dists.new'
    pool_dir = base_dir + '/pool'
    for i in PosixPath(pool_dir).iterdir():
        if not i.is_dir():
            continue
        branch_name = i.name
        component_name_list = []
        for j in PosixPath(pool_dir).joinpath(branch_name).iterdir():
            if not j.is_dir():
                continue
            component_name = j.name
            component_name_list.append(component_name)
            logger_rel.info('Generating Packages for %s-%s', branch_name, component_name)
            gen_packages(db, dist_dir, branch_name, component_name)
            logger_rel.info('Generating Contents for %s-%s', branch_name, component_name)
            gen_contents(db, branch_name, component_name, dist_dir)

        conf = conf_common.copy()
        conf.update(conf_branches[branch_name])
        logger_rel.info('Generating Release for %s', branch_name)
        gen_release(db, branch_name, component_name_list, dist_dir, conf)
    dist_dir_real = base_dir + '/dists'
    dist_dir_old = base_dir + '/dists.old'
    if PosixPath(dist_dir_real).exists():
        os.rename(dist_dir_real, dist_dir_old)
    os.rename(dist_dir, dist_dir_real)
    shutil.rmtree(dist_dir_old, True)


def gen_packages(db: sqlite3.Connection, dist_dir: str,
                 branch_name: str, component_name: str):
    repopath = branch_name + '/' + component_name
    basedir = PosixPath(dist_dir).joinpath(branch_name).joinpath(component_name)
    d = basedir.joinpath('binary-all')
    d.mkdir(0o755, parents=True, exist_ok=True)
    arch_packages = {'all': open(
        str(d.joinpath('Packages')), 'w', encoding='utf-8')}

    cur = db.cursor()
    cur.execute("SELECT p.package, p.architecture, p.filename, "
        "p.size, p.sha256, p.control "
        "FROM pv_packages p INNER JOIN pv_repos r ON p.repo=r.name "
        "WHERE r.path=?", (repopath,))
    for package, architecture, filename, size, sha256, control_json in cur:
        if architecture not in arch_packages:
            d = basedir.joinpath('binary-' + architecture)
            d.mkdir(0o755, parents=True, exist_ok=True)
            arch_packages[architecture] = open(
                str(d.joinpath('Packages')), 'w', encoding='utf-8')
        f = arch_packages[architecture]
        control = json.loads(control_json)
        control['Filename'] = filename
        control['Size'] = str(size)
        control['SHA256'] = sha256
        print(deb822.SortPackages(deb822.Packages(control)), file=f)
    for f in arch_packages.values():
        file_path = f.name
        f.close()
        subprocess.check_call(('xz', '-k', '-0', '-f', file_path))


def gen_contents(db: sqlite3.Connection,
                 branch_name: str, component_name: str, dist_dir: str):
    repopath = branch_name + '/' + component_name
    basedir = PosixPath(dist_dir).joinpath(branch_name).joinpath(component_name)
    basedir.mkdir(0o755, parents=True, exist_ok=True)
    cur = db.cursor()
    allarch = [r[0] for r in cur.execute("SELECT architecture FROM pv_repos "
        "WHERE architecture != 'all' AND path=?", (repopath,))]
    d = basedir.joinpath('Contents-all')
    d.mkdir(0o755, parents=True, exist_ok=True)
    for arch in allarch:
        cur.execute("""
            SELECT df.path || '/' || df.name AS f, group_concat(DISTINCT (
              json_extract(dp.control, '$.Section') || '/' || dp.package)) AS p
            FROM pv_packages dp
            INNER JOIN pv_package_files df USING (package, version, repopath)
            INNER JOIN pv_repos pr ON pr.name=dp.repo
            WHERE pr.path=? AND df.ftype='reg' AND pr.architecture IN (?, 'all')
            GROUP BY df.path, df.name""", (repopath, arch))
        filename = str(basedir.joinpath('Contents-%s.gz' % arch))
        with gzip.open(filename, 'wb', 9) as f:
            for path, package in cur:
                f.write((path.ljust(55) + ' ' + package + '\n').encode('utf-8'))


GPG_MAIN = os.environ.get('GPG', shutil.which('gpg2')) or shutil.which('gpg')

def gen_release(db: sqlite3.Connection, branch_name: str,
                component_name_list: list, dist_dir: str, conf: dict):
    branch_dir = PosixPath(dist_dir).joinpath(branch_name)
    if not branch_dir.exists():
        return

    cur = db.cursor()
    meta_data_list = dict.fromkeys(component_name_list)
    for component_name in component_name_list:
        cur.execute("SELECT architecture FROM pv_repos WHERE path=?",
            (branch_name + '/' + component_name,))
        meta_data_list[component_name] = [r[0] for r in cur] or ['all']
    cur.close()
    # Now we have this structure:
    # meta_data_list['main'] = ['amd64', 'arm64', ...]

    r_basic_info = {
        'Origin': conf['origin'],
        'Label': conf['label'],
        'Suite': branch_name,
        'Codename': conf['codename'],
        'Description': conf['desc'],
    }
    r_template = deb822.Release(r_basic_info)
    date_format = '%a, %d %b %Y %H:%M:%S %z'
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    r_template['Date'] = now.strftime(date_format)
    if 'ttl' in conf:
        ttl = int(conf['ttl'])
        r_template['Valid-Until'] = (
            now + datetime.timedelta(days=ttl)).strftime(date_format)

    r = r_template.copy()

    r['Architectures'] = ' '.join(sorted(set.union(*meta_data_list.values())))
    r['Components'] = ' '.join(sorted(component_name_list))
    hash_list = []
    for c in meta_data_list:
        for a in meta_data_list[c]:
            for filename in (
                'binary-%s/Packages' % a,
                'binary-%s/Packages.xz' % a,
                'Contents-%s' % a,
                'Contents-%s.gz' % a,
            ):
                path = branch_dir.joinpath(c).joinpath(filename)
                try:
                    size = path.stat().st_size
                except FileNotFoundError:
                    continue
                hash_list.append({
                    'sha256': sha256_file(str(path)),
                    'size': size,
                    'name': PurePath(c).joinpath(filename)
                })
    r['SHA256'] = hash_list
    release_fn = branch_dir.joinpath('Release')
    with open(str(release_fn), 'w', encoding='UTF-8') as f:
        f.write(str(r))
    subprocess.check_call([
        GPG_MAIN, '--batch', '--yes', '--clearsign',
        '-o', str(path.joinpath('InRelease')), str(release_fn)
    ])
    release_fn.unlink()
