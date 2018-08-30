import os
import subprocess
from binascii import hexlify
from datetime import timezone, timedelta
from pathlib import PosixPath, PurePath

from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

import deb822
from internal_db import get_collections
from internal_print import *


def legacy_path(legacy_dir: str, branch_name: str, component_name: str, arch: str):
    if arch == 'all':
        arch = 'noarch'
    d = PosixPath(legacy_dir).joinpath('os-' + arch)
    if component_name != 'main':
        d = d.joinpath(component_name)
    if branch_name != 'stable':
        d = d.joinpath(branch_name).joinpath('os-' + arch)
    d = d.joinpath('os3-dpkg')
    return d


def try_create_symlink(base: PosixPath, link_name: str, target: str, is_dir=False):
    try:
        base.joinpath(link_name).symlink_to(os.path.relpath(target, str(base)), target_is_directory=is_dir)
    except FileExistsError:
        pass


def generate(db: Database, base_dir: str, legacy_dir: str, conf_common: dict, conf_branches: dict):
    dist_dir = base_dir + '/dists'
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
            pkg_col, pkg_old_col, file_col = get_collections(db, branch_name, component_name)
            if legacy_dir is not None:
                gen_legacy(pkg_col, pkg_old_col, branch_name, component_name, dist_dir, pool_dir, legacy_dir)
            gen_packages(pkg_col, pkg_old_col, branch_name, component_name, dist_dir)
            # gen_contents(file_col, branch_name, component_name, dist_dir)

        conf = conf_common.copy()
        conf.update(conf_branches[branch_name])
        gen_release(db, branch_name, component_name_list, dist_dir, legacy_dir, conf)


def gen_legacy(pkg_col: Collection, pkg_old_col: Collection,
               branch_name: str, component_name: str, dist_dir: str, pool_dir: str, legacy_dir: str):
    def link_pool(arch):
        d = legacy_path(legacy_dir, branch_name, component_name, arch)
        d.mkdir(0o755, parents=True, exist_ok=True)
        try_create_symlink(d, 'pool', pool_dir, is_dir=True)
        contents_path = PosixPath(dist_dir).joinpath(branch_name).joinpath(component_name)
        packages_path = PosixPath(dist_dir).joinpath(branch_name).joinpath(component_name).joinpath('binary-' + arch)
        try_create_symlink(d, 'Packages', str(packages_path.joinpath('Packages')))
        try_create_symlink(d, 'Packages.xz', str(packages_path.joinpath('Packages.xz')))
        try_create_symlink(d, 'Contents-' + arch, str(contents_path.joinpath('Contents-' + arch)))
        try_create_symlink(d, 'Contents-' + arch + '.xz', str(contents_path.joinpath('Contents-' + arch + '.xz')))

    arch_list = pkg_col.aggregate([{'$group': {'_id': '$pkg.arch'}}])
    for a in arch_list:
        link_pool(a['_id'])
    arch_list = pkg_old_col.aggregate([{'$group': {'_id': '$pkg.arch'}}])
    for a in arch_list:
        link_pool(a['_id'])


def gen_packages(pkg_col: Collection, pkg_old_col: Collection,
                 branch_name: str, component_name: str, dist_dir: str):
    arch_packages = {}

    def print_packages_entry(e):
        arch = e['pkg']['arch']
        if arch not in arch_packages:
            d = PosixPath(dist_dir).joinpath(branch_name).joinpath(component_name).joinpath('binary-' + arch)
            d.mkdir(0o755, parents=True, exist_ok=True)
            arch_packages[arch] = open(str(d.joinpath('Packages')), 'w', encoding='utf-8')
        f = arch_packages[arch]

        e['control']['Filename'] = e['deb']['path']
        e['control']['Size'] = str(e['deb']['size'])
        e['control']['SHA256'] = hexlify(e['deb']['hash'])
        print(deb822.Deb822(e['control']), file=f)

    cur = pkg_col.find(
        {}, {'_id': 0, 'pkg': 1, 'deb': 1, 'control': 1}
    ).sort('pkg.name')
    for p in cur:
        print_packages_entry(p)
    cur = pkg_old_col.find(
        {}, {'_id': 0, 'pkg': 1, 'deb': 1, 'control': 1}
    ).sort([('pkg.name', ASCENDING), ('pkg.comp_ver', DESCENDING)])
    for p in cur:
        print_packages_entry(p)
    for a in arch_packages:
        file_path = arch_packages[a].name
        arch_packages[a].close()
        subprocess.check_call(['xz', '-k', '-0', '-f', file_path])


def gen_contents(file_col: Collection, branch_name: str, component_name: str, dist_dir: str):
    arch_packages = {}

    def print_contents_entry(e):
        arch = e['pkg']['arch']
        if arch not in arch_packages:
            d = PosixPath(dist_dir).joinpath(branch_name).joinpath(component_name)
            d.mkdir(0o755, parents=True, exist_ok=True)
            arch_packages[arch] = open(str(d.joinpath('Contents-' + arch)), 'w', encoding='utf-8')
        f = arch_packages[arch]

        print(e['path'], e['pkg']['name'], file=f)

    cur = file_col.find({'is_dir': False}, {'_id': 0, 'pkg.name': 1, 'pkg.arch': 1, 'path': 1}).sort('path')
    for i in cur:
        i['path'] = i['path'][1:]
        print_contents_entry(i)

    for a in arch_packages:
        file_path = arch_packages[a].name
        arch_packages[a].close()
        subprocess.check_call(['xz', '-k', '-0', '-f', file_path])


def _sha256_file(path: str):
    import Crypto.Hash.SHA256
    result = Crypto.Hash.SHA256.SHA256Hash()
    file_size = 0
    with open(path, 'rb') as file:
        while True:
            block = file.read(8192)
            if len(block) == 0:
                break
            result.update(block)
            file_size += len(block)
    return {
        'sha256': result.hexdigest(),
        'size': file_size,
    }


GPG_MAIN = ''


def _get_gpg_proc():
    global GPG_MAIN
    if GPG_MAIN == '':
        try:
            subprocess.run(['gpg2', '--version'], stdout=subprocess.DEVNULL)
            GPG_MAIN = 'gpg2'
        except FileNotFoundError:
            GPG_MAIN = 'gpg'
    return GPG_MAIN


def _output_and_sign(path: PosixPath, release: deb822.Release):
    print('Generate', path.joinpath('Release'))
    with open(str(path.joinpath('Release')), 'w', encoding='UTF-8') as release_file:
        print(release, file=release_file)
    print('Sign...')
    subprocess.check_call([
        _get_gpg_proc(), '--batch', '--yes', '--clearsign',
        '-o', str(path.joinpath('InRelease')),
        str(path.joinpath('Release'))
    ])
    path.joinpath('Release').unlink()


def gen_release(db: Database, branch_name: str, component_name_list: list,
                dist_dir: str, legacy_dir: str, conf: dict):
    branch_dir = PosixPath(dist_dir).joinpath(branch_name)
    if not branch_dir.exists():
        return

    meta_data_list = dict.fromkeys(component_name_list)
    for component_name in component_name_list:
        pkg_col, pkg_old_col, _ = get_collections(db, branch_name, component_name)
        arch_list = []
        pkg_arch = pkg_col.aggregate([{'$group': {'_id': '$pkg.arch'}}])
        for a in pkg_arch:
            arch_list.append(a['_id'])
        pkg_arch = pkg_old_col.aggregate([{'$group': {'_id': '$pkg.arch'}}])
        for a in pkg_arch:
            arch_list.append(a['_id'])
        meta_data_list[component_name] = dict.fromkeys(arch_list)

    # Now we have this structure:
    # meta_data_list['main']['amd64'] = None

    for c in meta_data_list:
        for a in meta_data_list[c]:
            files = []

            def add_file(p: str, path_for_legacy: str):
                path = branch_dir.joinpath(c).joinpath(p)
                if not path.exists():
                    return
                hash_result = _sha256_file(str(path))
                files.append({
                    'path': PurePath(c).joinpath(p),
                    'path_for_legacy': path_for_legacy,
                    'sha256': hash_result['sha256'],
                    'size': hash_result['size']
                })

            add_file('binary-%s/Packages' % a, 'Packages')
            add_file('binary-%s/Packages.xz' % a, 'Packages.xz')
            add_file('Contents-%s' % a, 'Contents-%s' % a)
            add_file('Contents-%s.xz' % a, 'Contents-%s.xz' % a)

            meta_data_list[c][a] = files

    r_basic_info = {
        'Origin': conf['origin'],
        'Label': conf['label'],
        'Suite': branch_name,
        'Codename': conf['codename'],
        'Description': conf['desc'],
    }
    r_template = deb822.Release(r_basic_info)
    date_format = '%a, %d %b %Y %H:%M:%S %z'
    now = datetime.now(tz=timezone.utc)
    r_template['Date'] = now.strftime(date_format)
    if 'ttl' in conf:
        ttl = int(conf['ttl'])
        r_template['Valid-Until'] = (now + timedelta(days=ttl)).strftime(date_format)

    r = r_template.copy()

    all_arch = []
    [all_arch.extend(meta_data_list[c].keys()) for c in meta_data_list]
    all_arch = list(set(all_arch))
    all_arch.sort()
    r['Architectures'] = ' '.join(all_arch)
    component_name_list.sort()
    r['Components'] = ' '.join(component_name_list)
    hash_list = []
    for c in meta_data_list:
        for a in meta_data_list[c]:
            for f in meta_data_list[c][a]:
                hash_list.append({
                    'sha256': f['sha256'],
                    'size': f['size'],
                    'name': f['path']
                })
    r['SHA256'] = hash_list
    _output_and_sign(branch_dir, r)

    if legacy_dir is not None:
        for c in meta_data_list:
            for a in meta_data_list[c]:
                target_dir = legacy_path(legacy_dir, branch_name, c, a)
                r = r_template.copy()
                r['Architectures'] = a
                hash_list = []
                for f in meta_data_list[c][a]:
                    hash_list.append({
                        'sha256': f['sha256'],
                        'size': f['size'],
                        'name': f['path_for_legacy']
                    })
                r['SHA256'] = hash_list
                _output_and_sign(target_dir, r)
