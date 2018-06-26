import re

_partitions = re.compile(r'^((?P<epoch>[0-9]+):)?(?P<body>[A-Za-z0-9.+~-]+)$')
_non_digit = re.compile(r'^[A-Za-z.+~]*')
_digit = re.compile(r'^[0-9]*')


def _break_down(ver: str):
    parts = _partitions.match(ver)
    if parts is None:
        raise AssertionError('malformed Version string')
    epoch = int(parts.group('epoch')) if parts.group('epoch') is not None else 0
    body = parts.group('body')
    upstream_version, debian_revision = body, ''
    if body.find('-') != -1:
        upstream_version, _, debian_revision = body.rpartition('-')
    return epoch, upstream_version, debian_revision


def _compare_body(body_a: str, body_b: str):
    def cut(ver: str, r):
        result = r.match(ver)
        if result is not None:
            return result.group(), ver[len(result.group()):]
        return '', ver

    def non_digit_mapping(ver: str):
        # Add '|' to indicate the end of string
        ver = (ver + '|').encode('ASCII')

        def m(n):
            if n == b'|'[0]:
                return 1  # Let the end of string be 1
            if n == b'~'[0]:
                return 0  # '~' should be even less than the end of string
            return n

        return bytes(map(m, ver))

    def digit_mapping(ver: str):
        return int(ver) if ver != '' else 0

    while True:
        sec_a, body_a = cut(body_a, _non_digit)
        sec_b, body_b = cut(body_b, _non_digit)
        sec_a, sec_b = non_digit_mapping(sec_a), non_digit_mapping(sec_b)
        for i in range(min(len(sec_a), len(sec_b))):
            if sec_a[i] - sec_b[i] != 0:
                return sec_a[i] - sec_b[i]
        # sec_a equals to sec_b
        if body_a + body_b == '':
            break
        sec_a, body_a = cut(body_a, _digit)
        sec_b, body_b = cut(body_b, _digit)
        sec_a, sec_b = digit_mapping(sec_a), digit_mapping(sec_b)
        if sec_a - sec_b != 0:
            return sec_a - sec_b
        # sec_a equals to sec_b
        if body_a + body_b == '':
            break
    return 0


def compare_ver(a: str, b: str):
    epoch_a, uv_a, dr_a = _break_down(a)
    epoch_b, uv_b, dr_b = _break_down(b)

    if epoch_a - epoch_b != 0:
        return epoch_a - epoch_b

    uv_delta = _compare_body(uv_a, uv_b)
    if uv_delta != 0:
        return uv_delta
    return _compare_body(dr_a, dr_b)
