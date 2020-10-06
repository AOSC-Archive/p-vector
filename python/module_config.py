import logging
import sys
from pathlib import PosixPath

from typing import Dict, Any, List

logger_conf = logging.getLogger('CONF')

PVConf = Dict[str, Any]
BranchesConf = Dict[str, Dict[str, Any]]

override_keys = ["codename", "desc", "label", "origin", "renew_in", "ttl"]
required_keys = ["codename", "desc", "label", "origin"]


def normalize_branch(conf_common: PVConf, conf_branch: PVConf) -> None:
    """ Populate missing config values in branch from default values
        String substitution is allowed within string typed keys, namely suite and desc:
            %BRANCH% will be replaced with the branch name
    """
    for key in override_keys:
        if key in conf_branch.keys():
            continue
        if key not in conf_common.keys() and key in required_keys:
            logger_conf.fatal(
                "Missing %s for branch %s which has no global default", key, conf_branch["branch"])
            sys.exit(1)
        if key not in conf_common.keys() and key not in required_keys:
            continue
        if key == "desc":
            conf_branch[key] = conf_common[key].replace("%BRANCH%", conf_branch["branch"])
        else:
            conf_branch[key] = conf_common[key]


def populate_branches(conf_common: PVConf, conf_branches: BranchesConf) -> None:
    """ Automatically create branches with directories on disk """
    pool_dir = conf_common['path'] + '/pool'
    for i in PosixPath(pool_dir).iterdir():
        if not i.is_dir():
            continue
        branch_name = i.name
        if branch_name in conf_branches.keys():
            # Do not touch ones already in YAML
            continue
        conf_branches[branch_name] = {"branch": branch_name}


def normalize(conf_common: PVConf, conf_branches: BranchesConf) -> None:
    if conf_common.get("populate", False):
        populate_branches(conf_common, conf_branches)
    for conf_branch in conf_branches.values():
        normalize_branch(conf_common, conf_branch)


def list_seen_repo(db) -> List[str]:
    ret = []
    cur = db.cursor()
    result = cur.execute("SELECT DISTINCT branch FROM pv_repos")
    cur.close()
    return ret


def run_gc(db) -> None:
    pass