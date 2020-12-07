import os
import sqlite3
import logging
import binascii
import tempfile
import threading

import zlib
import requests

URLBASE = 'https://packages.aosc.io/data/'

TABLES = (
    ("abbs.db", (
        "trees", "tree_branches", "packages", "package_duplicate",
        "package_versions", "package_spec", "package_dependencies",
        "dpkg_repo_stats"
    )),
    ("piss.db", (
        "upstream_status", "package_upstream", "anitya_link", "anitya_projects"
    )),
)
SRCREPOS = ("aosc-os-abbs",)
MARKS_TABLES = (
    "marks", "committers", "package_rel", "package_basherr", "branches")
MARKS_DB_SFX = "-marks.db"

logger_sync = logging.getLogger('SYNC')

def download_db(url, filename, etag=None):
    headers = {'If-None-Match': etag}
    r = requests.get(url, headers=headers, stream=True, timeout=30)
    r.raise_for_status()
    newetag = r.headers.get('ETag')
    if r.status_code == 304:
        r.close()
        return newetag
    dec = zlib.decompressobj(zlib.MAX_WBITS | 16)
    with open(filename, 'wb') as f:
        while True:
            buf = r.raw.read(8192)
            if not buf:
                break
            f.write(dec.decompress(buf))
        f.write(dec.flush())
    r.close()
    return newetag

def escape_val(x):
    if isinstance(x, str):
        return x.replace('\\', '\\\\').replace('\r', '\\r').replace(
            '\n', '\\n').replace('\t', '\\t')
    elif isinstance(x, bytes):
        return '\\x' + binascii.b2a_hex(x).decode('ascii')
    elif x is None:
        return '\\N'
    else:
        return str(x)

def make_copy(dbname, table, fd, idxcol=None):
    try:
        db = sqlite3.connect(dbname)
        cur = db.execute("SELECT * FROM " + table)
    except Exception:
        os.close(fd)
        raise
    with open(fd, 'w', encoding='utf-8') as f:
        for row in cur:
            if idxcol is not None:
                f.write(escape_val(idxcol) + '\t')
            f.write('\t'.join(map(escape_val, row)))
            f.write('\n')
    db.close()

def sync_table(cur, dbname, table, idxcol=None, prefix=None):
    logger_sync.info('- Table %s', table)
    if prefix:
        pgtable = prefix + table
    else:
        pgtable = table
    pr, pw = os.pipe()
    thr = threading.Thread(target=make_copy, args=(dbname, table, pw, idxcol))
    thr.start()
    with open(pr, 'rb') as f:
        cur.copy_from(f, pgtable)
    thr.join()

def sync_db(db):
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pv_dbsync ("
                "name TEXT PRIMARY KEY,"
                "etag TEXT,"
                "updated TIMESTAMP WITH TIME ZONE DEFAULT (now())"
                ")")
    cur.execute("SELECT name, etag FROM pv_dbsync")
    etags = dict(cur)
    sqlfile = os.path.join(os.path.dirname(__file__), 'abbsdb.sql')
    with open(sqlfile, 'r', encoding='utf-8') as f:
        cur.execute(f.read())
    db.commit()
    with tempfile.TemporaryDirectory() as tmpdir:
        for dbname, tables in TABLES:
            filename = os.path.join(tmpdir, dbname)
            newetag = download_db(
                URLBASE + dbname + '.gz', filename, etags.get(dbname))
            if newetag == etags.get(dbname):
                logger_sync.info('Skip %s', dbname)
                continue
            logger_sync.info('Syncing %s', dbname)
            cur.execute("DELETE FROM pv_dbsync WHERE name=%s", (dbname,))
            cur.execute("INSERT INTO pv_dbsync (name, etag) VALUES (%s,%s)", (dbname, newetag))
            for table in tables:
                cur.execute("TRUNCATE " + table)
                sync_table(cur, filename, table)
            os.remove(filename)
            db.commit()
        cur.execute("SELECT name, tid FROM trees")
        treeids = dict(cur)
        for table in MARKS_TABLES:
            cur.execute("TRUNCATE repo_" + table)
        for srcrepo in SRCREPOS:
            dbname = srcrepo + MARKS_DB_SFX
            tid = treeids[srcrepo]
            filename = os.path.join(tmpdir, dbname)
            newetag = download_db(
                URLBASE + dbname + '.gz', filename, etags.get(dbname))
            if newetag == etags.get(dbname):
                logger_sync.info('Skip %s', dbname)
                continue
            cur.execute("DELETE FROM pv_dbsync WHERE name=%s", (dbname,))
            cur.execute("INSERT INTO pv_dbsync (name, etag) VALUES (%s,%s)", (dbname, newetag))
            logger_sync.info('Syncing %s', dbname)
            for table in MARKS_TABLES:
                sync_table(cur, filename, table, tid, 'repo_')
            os.remove(filename)
            db.commit()
