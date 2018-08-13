import pymongo

from pymongo.collection import Collection
from pymongo.database import Database


def get_collections(db: Database, branch: str, component: str) -> (Collection, Collection, Collection):
    col_name = '%s/%s' % (branch, component)
    pkg_col = db[col_name]
    pkg_col.create_index([('deb.hash', pymongo.ASCENDING)], unique=True)
    pkg_col.create_index([('deb.path', pymongo.ASCENDING)], unique=True)
    pkg_col.create_index([('pkg', pymongo.ASCENDING)], unique=True)
    pkg_col.create_index([
        ('pkg.name', pymongo.ASCENDING),
        ('pkg.arch', pymongo.ASCENDING)],
        name='pkg_one_version', unique=True)
    pkg_col.create_index([('pkg.arch', pymongo.ASCENDING)])

    pkg_old_col = db[col_name + '.old']
    pkg_old_col.create_index([('deb.hash', pymongo.ASCENDING)], unique=True)
    pkg_old_col.create_index([('pkg', pymongo.ASCENDING)], unique=True)
    pkg_old_col.create_index([('pkg.arch', pymongo.ASCENDING)])

    file_col = db[col_name + '.files']
    file_col.create_index([('path', pymongo.ASCENDING)])
    file_col.create_index([('pkg', pymongo.ASCENDING)])
    file_col.create_index([('pkg.arch', pymongo.ASCENDING)])

    return pkg_col, pkg_old_col, file_col
