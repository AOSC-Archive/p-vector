import os
from pathlib import PosixPath

import re
import signal
import sys
import threading
from subprocess import CalledProcessError

import bson
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

import internal_dpkg_version
import internal_pkgscan
from internal_db import get_collections
from internal_print import *

base_dir = ''
pool_dir = ''
interrupted = False


def split_soname(s: str):
    r = re.compile('\.so(?!=[$.])')
    pos = r.search(s)
    if pos is None:
        return {'name': s, 'ver': ''}
    return {'name': s[:pos.end()], 'ver': s[pos.end():]}


def doc_from_pkg_scan(p):
    hash_value = bytes(p.p['hash_value'])
    pkg_doc = {
        'pkg': {
            'name': p.control['Package'],
            'ver': p.control['Version'],
            'comp_ver': internal_dpkg_version.comparable_ver(p.control['Version']),
            'arch': p.control['Architecture'],
        },
        'deb': {
            'path': p.filename,
            'size': bson.int64.Int64(p.p['size']),
            'hash': hash_value,
            'mtime': p.mtime
        },
        'time': p.p['time'],
        'control': p.control,
        'relation': p.control.relations,
        'so_provides': [split_soname(i) for i in p.p['so_provides']],
        'so_depends': [split_soname(i) for i in p.p['so_depends']],
    }
    file_doc = []
    for f in p.p['files']:
        doc = {
            'deb': hash_value,
            'pkg': pkg_doc['pkg'],
            'path': f['path'],
            'is_dir': f['is_dir'],
            'size': bson.int64.Int64(f['size']),
            'type': f['type'],
            'perm': f['perm'],
            'uid': f['uid'],
            'gid': f['gid'],
            'uname': f['uname'],
            'gname': f['gname'],
        }
        doc['path'] = os.path.normpath(os.path.join('/', doc['path']))
        doc['base'] = os.path.basename(doc['path'])
        file_doc.append(doc)
    return pkg_doc, file_doc


def prune(pkg_col: Collection, pkg_old_col: Collection, file_col: Collection):
    delete_list = []
    delete_old_list = []

    cur = pkg_col.find()
    total = cur.count()
    count = 0
    for i in cur:
        if not PosixPath(base_dir).joinpath(i['deb']['path']).exists():
            delete_list.append((i['deb']['path'], i['pkg']))
        count += 1
        progress_bar('Check current', count / total)

    cur = pkg_old_col.find()
    total = cur.count()
    count = 0
    for i in cur:
        if not PosixPath(base_dir).joinpath(i['deb']['path']).exists():
            delete_old_list.append(i['deb']['path'])
        count += 1
        progress_bar('Check archive', count / total)

    total = len(delete_list)
    count = 0
    for i in delete_list:
        I('CLEAN', 'CUR   ', i[0])
        pkg_col.delete_many({'deb.path': i[0]})
        file_col.delete_many({'pkg': i[1]})
        count += 1
        progress_bar('Prune current', count / total)

    total = len(delete_old_list)
    count = 0
    for i in delete_old_list:
        I('CLEAN', 'OLD   ', i)
        pkg_old_col.delete_many({'deb.path': i})
        count += 1
        progress_bar('Prune archive', count / total)

    progress_bar_end('Prune database')
    return


def _scan(pkg_col: Collection, pkg_old_col: Collection, file_col: Collection, branch: str, component: str):
    from concurrent.futures import ThreadPoolExecutor
    executor = ThreadPoolExecutor(max_workers=os.cpu_count() + 1)
    futures = []
    counter_lock = threading.Lock()
    count = 0
    total = 0

    def signal_handler(_sig, _frame):
        global interrupted
        interrupted = True
        for future in futures:
            future.cancel()
        W('SCAN', 'Received SIGINT. Cancelled pending jobs.', file=sys.stderr)

    signal.signal(signal.SIGINT, signal_handler)

    def scan_deb(rel_path: str, mtime: int, status: str):
        deb_path = PosixPath(base_dir).joinpath(rel_path)
        # Scan it.
        try:
            p = internal_pkgscan.scan(str(deb_path))
        except CalledProcessError as e:
            if e.returncode < 0 and signal.Signals(-e.returncode) == signal.SIGINT:
                W('SCAN', 'INTR  ', rel_path, file=sys.stderr)
                return
            if e.returncode in [1, 2]:
                E('SCAN', 'ERROR ', rel_path, 'is corrupted, status:', e.returncode)
                return
            raise
        if interrupted:
            return
        # Make a new document
        p.filename = rel_path
        p.mtime = mtime
        pkg_doc, file_doc = doc_from_pkg_scan(p)

        '''
        pkg_doc: meta info of this package
        file_doc: file list of this package
        
        if update in place:
            pkg_doc (key:deb.path) =replace> [pkg]
            file_doc (key:deb.hash_value) =replace> [files]
        else (new deb file):
            given an index: (name, arch) is unique
            try to replace an old package or insert in [pkg], put the old one to old_pkg...
                failed (DuplicateKeyError):
                    it cannot find the older one and tried to insert itself, but:
                    if found pkg_doc in pkg:
                        they have a same version. DUP
                    else:
                        this is the oldest one. OLD
                        insert pkg_doc into [pkg_old]
                success:
                    if replaced:
                        this is the newest one. NEWER
                        insert file_doc into [files]
                        insert old_pkg into [pkg_old]
                    else (inserted):
                        this is a new package. NEW
                        insert file_doc into [files]
                    
        '''

        if status == 'update':
            # if a document points to the same path exists, replace it
            old_pkg = pkg_col.find_one_and_replace(
                {'deb.path': rel_path}, pkg_doc, {'_id': False}, upsert=False)
            if old_pkg is None:
                pkg_old_col.replace_one({'deb.path': rel_path}, pkg_doc)
            else:
                file_col.delete_many({'pkg': pkg_doc['pkg']})
                file_col.insert_many(file_doc)
            I('SCAN', 'UPDATE', rel_path)
        else:
            # if this is a new document
            try:
                old_pkg = pkg_col.find_one_and_replace(
                    {'pkg.name': pkg_doc['pkg']['name'],
                     'pkg.arch': pkg_doc['pkg']['arch'],
                     'pkg.comp_ver': {'$lt': pkg_doc['pkg']['comp_ver']}
                     }, pkg_doc, {'_id': False}, upsert=True)
            except DuplicateKeyError:
                same_ver_pkg = pkg_col.find_one({'pkg': pkg_doc['pkg']})
                if same_ver_pkg is None:
                    # This one is older, we do nothing. We had better delete it.
                    pkg_old_col.insert_one(pkg_doc)
                    W('SCAN', 'OLD   ', pkg_doc['pkg']['arch'], pkg_doc['pkg']['name'], pkg_doc['pkg']['ver'])
                else:
                    E('SCAN', 'DUP   ', rel_path, '==', same_ver_pkg['deb']['path'])
                return
            if old_pkg is not None:
                # This one is newer, put the old one into archive, insert this one.
                pkg_old_col.insert_one(old_pkg)
                file_col.delete_many({'pkg': old_pkg['pkg']})
                file_col.insert_many(file_doc)
                I('SCAN', 'NEWER ', pkg_doc['pkg']['arch'], pkg_doc['pkg']['name'],
                  pkg_doc['pkg']['ver'], '>>', old_pkg['pkg']['ver'])
            else:
                # Completely new package
                file_col.insert_many(file_doc)
                I('SCAN', 'NEW   ', pkg_doc['pkg']['arch'], pkg_doc['pkg']['name'], pkg_doc['pkg']['ver'])

    def containment_shell(*args):
        nonlocal count
        try:
            scan_deb(*args)
        except Exception as e:
            import logging
            E('SCAN', e, 'with', args, file=sys.stderr)
            logging.exception(e)
            raise
        finally:
            with counter_lock:
                count += 1
            progress_bar('Scan .deb', count / total)

    deb_files = {}
    search_path = PosixPath(pool_dir).joinpath(branch).joinpath(component)
    for i in search_path.rglob('*.deb'):
        if not i.is_file():
            continue
        s = i.stat()
        deb_files[str(i.relative_to(base_dir))] = {
            'size': s.st_size,
            'mtime': int(s.st_mtime),
            'status': 'new'
        }

    def filter_deb_files(pkg_in_db: Cursor, files: dict):
        for cur in pkg_in_db:
            '''
            Suppose there are no changes if it has:
            * the same path (unique);
            * the same size;
            * the same modify time.
            We will not try to calculate hash now because it is too costly.
            '''
            path = cur['deb']['path']
            mtime = cur['deb']['mtime']
            size = cur['deb']['size']
            if files[path]['mtime'] != mtime or files[path]['size'] != size:
                files[path]['status'] = 'update'
            else:
                del files[path]

    query_exist = {'deb.path': {'$in': [path for path in deb_files]}}
    project_exist = {'_id': False, 'deb': True}
    filter_deb_files(pkg_old_col.find(query_exist, project_exist), deb_files)
    filter_deb_files(pkg_col.find(query_exist, project_exist), deb_files)

    total = len(deb_files)
    with executor:
        for path in deb_files:
            futures.append(executor.submit(
                containment_shell, path, deb_files[path]['mtime'], deb_files[path]['status']))
    if not interrupted:
        progress_bar_end('Scan .deb')
    else:
        print()


def scan(db: Database, base_dir_: str):
    global base_dir, pool_dir
    base_dir = base_dir_
    pool_dir = base_dir_ + '/pool'

    for i in PosixPath(pool_dir).iterdir():
        if not i.is_dir():
            continue
        branch_name = i.name
        print('====', branch_name, '====')
        for component_dir in PosixPath(pool_dir).joinpath(branch_name).iterdir():
            if not component_dir.is_dir():
                continue
            component_name = component_dir.name
            pkg_col, pkg_old_col, file_col = get_collections(db, branch_name, component_name)
            print(branch_name, component_name)
            _scan(pkg_col, pkg_old_col, file_col, branch_name, component_name)
            if interrupted:
                return
