
def make_insert(d):
    keys, values = zip(*d.items())
    return ', '.join(keys), ', '.join(('%s',) * len(values)), values

def make_update(d):
    keys, values = zip(*d.items())
    return ', '.join(k + '=%s' for k in keys), values

def make_where(d):
    keys, values = zip(*d.items())
    return ' AND '.join(k + '=%s' for k in keys), values

def init_db(db, dbtype='sqlite'):
    cur = db.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS pv_repos ('
                'name TEXT PRIMARY KEY,' # key: bsp-sunxi-armel/testing
                'realname TEXT,'     # group key: amd64, bsp-sunxi-armel
                'path TEXT,'         # testing/main
                'testing INTEGER,'   # 0, 1, 2
                'branch TEXT,'       # stable, testing, explosive
                'component TEXT,'    # main, bsp-sunxi, opt-avx2
                'architecture TEXT'  # amd64, all
                ')')
    cur.execute('CREATE TABLE IF NOT EXISTS pv_packages ('
                'package TEXT,'
                'version TEXT,'
                'repo TEXT,'
                'architecture TEXT,'
                'filename TEXT,'
                'size INTEGER,'
                'sha256 TEXT,'
                'mtime INTEGER,'
                'debtime INTEGER,'
                'section TEXT,'
                'installed_size INTEGER,'  # x1024
                'maintainer TEXT,'
                'description TEXT,'
                '_vercomp TEXT,'
                'PRIMARY KEY (package, version, repo)'
                ')')
    cur.execute('CREATE TABLE IF NOT EXISTS pv_package_duplicate ('
                'package TEXT,'
                'version TEXT,'
                'repo TEXT,'
                'architecture TEXT,'
                'filename TEXT,'
                'size INTEGER,'
                'sha256 TEXT,'
                'mtime INTEGER,'
                'debtime INTEGER,'
                'section TEXT,'
                'installed_size INTEGER,'  # x1024
                'maintainer TEXT,'
                'description TEXT,'
                '_vercomp TEXT,'
                'PRIMARY KEY (filename)'
                ')')
    cur.execute('CREATE TABLE IF NOT EXISTS pv_package_dependencies ('
                'package TEXT,'
                'version TEXT,'
                'repo TEXT,'
                'depends TEXT,'
                'pre_depends TEXT,'
                'recommends TEXT,'
                'suggests TEXT,'
                'enhances TEXT,'
                'breaks TEXT,'
                'conflicts TEXT,'
                'PRIMARY KEY (package, version, repo)'
                ')')
    cur.execute('CREATE TABLE IF NOT EXISTS pv_package_sodep ('
                'package TEXT,'
                'version TEXT,'
                'repo TEXT,'
                'depends INTEGER,' # 0 provides, 1 depends
                'name TEXT,'
                'ver TEXT'
                # 'PRIMARY KEY (package, version, repo, depends, name)'
                ')')
    cur.execute('CREATE TABLE IF NOT EXISTS pv_package_files ('
                'package TEXT,'
                'version TEXT,'
                'repo TEXT,'
                'path TEXT,'
                'name TEXT,'
                'size INTEGER,'
                'ftype TEXT,'
                'perm INTEGER,'
                'uid INTEGER,'
                'gid INTEGER,'
                'uname TEXT,'
                'gname TEXT'
                # 'PRIMARY KEY (package, version, repo, path, name)'
                ')')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_repos_path'
                ' ON pv_repos (path, architecture)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_repos_architecture'
                ' ON pv_repos (architecture, testing)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_packages_repo'
                ' ON pv_packages (repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_duplicate_package'
                ' ON pv_package_duplicate (package, version, repo)')
    db.commit()
    cur.close()

def init_index(db):
    cur = db.cursor()
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_packages_vercomp'
                ' ON pv_packages (repo, package, _vercomp)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_sodep_package'
                ' ON pv_package_sodep (package, version, repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_sodep_name'
                ' ON pv_package_sodep (name, repo) WHERE depends=0')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_files_package'
                ' ON pv_package_files (package, version, repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_files_path_name'
                ' ON pv_package_files (path, name)')
    db.commit()
    cur.close()
