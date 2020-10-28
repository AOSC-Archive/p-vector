import os
from pathlib import PosixPath

import logging
import binascii
import functools
import urllib.parse
import multiprocessing.dummy
from subprocess import CalledProcessError

from typing import List

import module_config

logger_gc = logging.getLogger('GC')


def purge_from_db(db, branch_component: List[str]):
    cur = db.cursor()
    for i in branch_component:
        logger_gc.info("%s removed from database", i)
        cur.execute("DELETE FROM pv_repos WHERE path = %s", (i, ))
    db.commit()
    cur.close()


def run_gc(db, base_dir: str, dry_run: bool):
    repos = module_config.list_seen_repo(db)
    pool_dir = base_dir + '/pool'
    to_delete = []
    # Scan if any of the repos are missing
    for i in repos:
        path = PosixPath(pool_dir).joinpath(i)
        if not path.is_dir():
            to_delete.append(i)
            logger_gc.info("%s will be removed from the database", i)

    if not dry_run:
        purge_from_db(db, to_delete)
    else:
        logger_gc.info("DRY RUN - database is unmodified")