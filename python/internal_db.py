
import os
import psycopg2

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
                'size BIGINT,'
                'sha256 TEXT,'
                'mtime INTEGER,'
                'debtime INTEGER,'
                'section TEXT,'
                'installed_size BIGINT,'  # x1024
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
                'size BIGINT,'
                'sha256 TEXT,'
                'mtime INTEGER,'
                'debtime INTEGER,'
                'section TEXT,'
                'installed_size BIGINT,'  # x1024
                'maintainer TEXT,'
                'description TEXT,'
                '_vercomp TEXT,'
                'PRIMARY KEY (filename)'
                ')')
    cur.execute('CREATE TABLE IF NOT EXISTS pv_package_dependencies ('
                'package TEXT,'
                'version TEXT,'
                'repo TEXT,'
                'relationship TEXT,'
                'value TEXT,'
                'PRIMARY KEY (package, version, repo, relationship)'
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
                'size BIGINT,'
                'ftype TEXT,'
                'perm INTEGER,'
                'uid BIGINT,'
                'gid BIGINT,'
                'uname TEXT,'
                'gname TEXT'
                # 'PRIMARY KEY (package, version, repo, path, name)'
                ')')
    cur.execute('CREATE MATERIALIZED VIEW IF NOT EXISTS v_packages_new AS '
                'SELECT DISTINCT ON (repo, package) package, version, repo, '
                '  architecture, filename, size, sha256, mtime, debtime, '
                '  section, installed_size, maintainer, description '
                'FROM pv_packages '
                'ORDER BY repo, package, _vercomp DESC')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_repos_path'
                ' ON pv_repos (path, architecture)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_repos_architecture'
                ' ON pv_repos (architecture, testing)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_packages_repo'
                ' ON pv_packages (repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_duplicate_package'
                ' ON pv_package_duplicate (package, version, repo)')
    db.commit()
    try:
        cur.execute("SELECT 'comparable_dpkgver'::regproc")
    except psycopg2.ProgrammingError:
        db.rollback()
        sqlfile = os.path.join(os.path.dirname(__file__), 'vercomp.sql')
        with open(sqlfile, 'r', encoding='utf-8') as f:
            cur.execute(f.read())
            db.commit()
    cur.close()

def init_index(db):
    cur = db.cursor()
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_packages_vercomp'
                ' ON pv_packages (repo, package, _vercomp DESC)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_sodep_package'
                ' ON pv_package_sodep (package, version, repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_sodep_name'
                ' ON pv_package_sodep (name, repo) WHERE depends=0')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_files_package'
                ' ON pv_package_files (package, version, repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_files_path_name'
                ' ON pv_package_files (path, name)')
    cur.execute('REFRESH MATERIALIZED VIEW v_packages_new')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_v_packages_new_package'
                ' ON v_packages_new (package, version, repo)')
    db.commit()
    cur.close()
