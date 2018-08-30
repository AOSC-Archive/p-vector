import time

import zmq

ctx = zmq.Context()
zmq_change = 'ipc:///tmp/p-vector-changes'
publisher = ctx.socket(zmq.PUB)


def init():
    publisher.bind(zmq_change)
    time.sleep(1)


def publish_change(comp: str, pkg: str, arch: str, method: str, from_ver: str, to_ver: str):
    publisher.send_json({
        'comp': comp,
        'pkg': pkg,
        'arch': arch,
        'method': method,
        'from_ver': from_ver,
        'to_ver': to_ver,
    })
