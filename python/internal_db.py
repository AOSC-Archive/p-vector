
import os
import logging
import psycopg2

logger_db = logging.getLogger('DB')

def make_insert(d):
    keys, values = zip(*d.items())
    return ', '.join(keys), ', '.join(('%s',) * len(values)), values

def make_update(d):
    keys, values = zip(*d.items())
    return ', '.join(k + '=%s' for k in keys), values

def make_where(d):
    keys, values = zip(*d.items())
    return ' AND '.join(k + '=%s' for k in keys), values

SQL_v_dpkg_dependencies = '''
CREATE MATERIALIZED VIEW IF NOT EXISTS v_dpkg_dependencies AS
SELECT package, version, repo, relationship, nr,
  depspl[1] deppkg, depspl[2] deparch, depspl[3] relop, depspl[4] depver,
  comparable_dpkgver(depspl[4]) depvercomp
FROM (
  SELECT package, version, repo, relationship, nr, regexp_match(dep,
    '^\s*([a-zA-Z0-9.+-]{2,})(?::([a-zA-Z0-9][a-zA-Z0-9-]*))?' ||
    '(?:\s*\(\s*([>=<]+)\s*([0-9a-zA-Z:+~.-]+)\s*\))?(?:\s*\[[\s!\w-]+\])?' ||
    '\s*(?:<.+>)?\s*$') depspl
  FROM (
    SELECT package, version, repo, relationship, nr,
      unnest(string_to_array(dep, '|')) dep
    FROM (
      SELECT d.package, d.version, d.repo, d.relationship, v.nr, v.val dep
      FROM pv_package_dependencies d
      INNER JOIN v_packages_new n USING (package, version, repo)
      INNER JOIN LATERAL unnest(string_to_array(d.value, ','))
        WITH ORDINALITY AS v(val, nr) ON TRUE
    ) q1
  ) q2
) q3
'''

SQL_v_so_breaks = '''
CREATE MATERIALIZED VIEW IF NOT EXISTS v_so_breaks AS
SELECT sp.package, sp.repo, sp.name soname, sp.ver sover,
  sd.package dep_package, sd.repo dep_repo, sd.version dep_version
FROM pv_package_sodep sp
INNER JOIN v_packages_new vp USING (package, version, repo)
INNER JOIN pv_repos rp ON rp.name=sp.repo
INNER JOIN pv_repos rd ON rd.architecture IN (rp.architecture, 'all')
AND rp.testing<=rd.testing AND rp.component IN (rd.component, 'main')
INNER JOIN pv_package_sodep sd ON sd.depends=1
AND sd.repo=rd.name AND sd.name=sp.name AND sd.package!=sp.package
AND (sp.ver=sd.ver OR sp.ver LIKE sd.ver || '.%')
INNER JOIN v_packages_new vp2
ON vp2.package=sd.package AND vp2.version=sd.version AND vp2.repo=sd.repo
WHERE sp.depends=0
UNION ALL
SELECT sp.package, sp.repo, sp.name soname, sp.ver sover,
  pi.package dep_package, pi.repo dep_repo, pi.version dep_version
FROM pv_package_sodep sp
INNER JOIN v_packages_new vp USING (package, version, repo)
INNER JOIN pv_repos rp ON rp.name=sp.repo
INNER JOIN pv_repos rd ON rd.architecture IN (rp.architecture, 'all')
AND rp.testing<=rd.testing AND rp.component IN (rd.component, 'main')
INNER JOIN pv_package_issues pi
ON pi.repo=rd.name AND pi.package!=sp.package
AND substring(pi.filename from 1 for position('.so' in pi.filename)+2)=sp.name
AND (sp.ver || '.') LIKE (detail->>'sover_provide') || '.%'
AND pi.errno=431 AND pi.detail IS NOT NULL
WHERE sp.depends=0
'''

def init_db(db):
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
    cur.execute('CREATE TABLE IF NOT EXISTS pv_package_issues ('
                'id SERIAL,'
                'package TEXT,'
                'version TEXT,'
                'repo TEXT,'
                'errno INTEGER,'
                'level SMALLINT,'
                'filename TEXT,'
                'ctime TIMESTAMP WITH TIME ZONE DEFAULT (now()),'
                'mtime TIMESTAMP WITH TIME ZONE DEFAULT (now()),'
                'atime TIMESTAMP WITH TIME ZONE DEFAULT (now()),'
                'detail JSONB,'
                'UNIQUE (package, version, repo, errno, filename)'
                ')')
    cur.execute('CREATE MATERIALIZED VIEW IF NOT EXISTS v_packages_new AS '
                'SELECT DISTINCT ON (repo, package) package, version, repo, '
                '  architecture, filename, size, sha256, mtime, debtime, '
                '  section, installed_size, maintainer, description, _vercomp '
                'FROM pv_packages '
                'WHERE debtime IS NOT NULL '
                'ORDER BY repo, package, _vercomp DESC')
    cur.execute(SQL_v_dpkg_dependencies)
    cur.execute(SQL_v_so_breaks)
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_repos_path'
                ' ON pv_repos (path, architecture)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_repos_architecture'
                ' ON pv_repos (architecture, testing)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_packages_repo'
                ' ON pv_packages (repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_duplicate_package'
                ' ON pv_package_duplicate (package, version, repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_issues_errno'
                ' ON pv_package_issues (errno)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_issues_mtime'
                ' ON pv_package_issues USING brin (mtime)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_issues_atime'
                ' ON pv_package_issues (atime)')
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

def init_index(db, refresh=True):
    cur = db.cursor()
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_packages_mtime'
                ' ON pv_packages (mtime)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_sodep_package'
                ' ON pv_package_sodep (package, version, repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_sodep_name'
                ' ON pv_package_sodep (name, repo) WHERE depends=0')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_files_package'
                ' ON pv_package_files (package, version, repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_files_path'
                ' ON pv_package_files (path)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pv_package_files_name'
                ' ON pv_package_files (name)')
    if refresh:
        cur.execute('REFRESH MATERIALIZED VIEW v_packages_new')
        cur.execute('REFRESH MATERIALIZED VIEW v_dpkg_dependencies')
        cur.execute('REFRESH MATERIALIZED VIEW v_so_breaks')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_v_packages_new_package'
                ' ON v_packages_new (package, version, repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_v_packages_new_mtime'
                ' ON v_packages_new (mtime)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_v_dpkg_dependencies_package'
                ' ON v_dpkg_dependencies (package, version, repo)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_v_dpkg_dependencies_dep'
                ' ON v_dpkg_dependencies (relationship, deppkg, depvercomp)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_v_so_breaks_package'
                ' ON v_so_breaks (package)')
    db.commit()
    cur.close()

TABLES_PV = ('pv_package_dependencies', 'pv_package_duplicate',
    'pv_package_files', 'pv_package_sodep', 'pv_packages', 'pv_repos',
    'pv_package_issues')

TABLES_PKGS = ('pv_dbsync', 'trees', 'tree_branches', 'packages',
    'package_duplicate', 'package_versions', 'package_spec',
    'package_dependencies', 'dpkg_repo_stats', 'upstream_status', 
    'package_upstream', 'anitya_link', 'anitya_projects', 'repo_marks', 
    'repo_committers', 'repo_package_rel', 'repo_branches')

def drop_tables(db, ttype):
    cur = db.cursor()
    if ttype in ('all', 'pv'):
        for table in TABLES_PV:
            cur.execute("DROP TABLE IF EXISTS %s CASCADE" % table)
            logger_db.info(cur.query.decode('utf-8'))
    if ttype in ('all', 'sync'):
        for table in TABLES_PKGS:
            cur.execute("DROP TABLE IF EXISTS %s CASCADE" % table)
            logger_db.info(cur.query.decode('utf-8'))
    for note in db.notices:
        logger_db.info(note)
    db.commit()

def analyze_issues(db, full=False):
    cur = db.cursor()
    logger_db.info('Analyzing packaging issues...')
    if full:
        cur.execute("UPDATE pv_package_issues SET atime='1970-01-01'")
        logger_db.info(cur.statusmessage)
    sqlfile = os.path.join(os.path.dirname(__file__), 'pkgissues.sql')
    with open(sqlfile, 'r', encoding='utf-8') as f:
        cur.execute(f.read())
    logger_db.info(cur.statusmessage)
    logger_db.info('Done.')
    db.commit()
