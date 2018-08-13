import json
import os

import deb822


class PkgInfoWrapper(object):
    control = None
    filename = ''
    p = None

    def __init__(self, p):
        self.control = deb822.Packages(p['control'])
        self.p = p


def scan(path: str):
    import subprocess
    result = subprocess.check_output([os.path.dirname(__file__) + '/pkgscan_cli', path],
                                     stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return PkgInfoWrapper(json.loads(result.decode('utf-8')))
