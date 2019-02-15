import re

_partitions = re.compile(r'^((?P<epoch>[0-9]+):)?(?P<body>[A-Za-z0-9.+~-]+)$')
_non_digit = re.compile(r'^[A-Za-z.+~-]*')
_digit = re.compile(r'^[0-9]*')

RE_ALL_DIGITS_OR_NOT = re.compile("\d+|\D+")
RE_DIGITS = re.compile("\d+")
RE_ALPHA = re.compile("[A-Za-z]")

def _break_down(ver: str):
    parts = _partitions.match(ver)
    if parts is None:
        raise AssertionError('malformed Version string')
    epoch = parts.group('epoch') if parts.group('epoch') is not None else '0'
    body = parts.group('body')
    upstream_version, debian_revision = body, ''
    if body.find('-') != -1:
        upstream_version, _, debian_revision = body.rpartition('-')
    return epoch, upstream_version, debian_revision


def _comparable_digit(i: str):
    clean_number = i.lstrip('0')
    if clean_number == '':
        clean_number = '0'
    length = len(clean_number)
    if not (1 <= length <= 26):
        raise AssertionError('malformed number string')
    return chr(ord('0') + (length - 1)) + clean_number


def _comparable_non_digit(s: str):
    # Add '|' to indicate the end of string
    s = (s + '|').encode('ASCII')
    table = '~|ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxy+-.'

    def m(n):
        return ord('0') + table.index(chr(n))

    return bytes(map(m, s)).decode('ASCII')


def _comparable_body(body: str):
    def cut(ver: str, r):
        result = r.match(ver)
        if result is not None:
            return result.group(), ver[len(result.group()):]
        return '', ver

    output_body = ''
    while True:
        sec, body = cut(body, _non_digit)
        sec = _comparable_non_digit(sec)
        output_body += sec
        if body == '':
            break
        sec, body = cut(body, _digit)
        sec = _comparable_digit(sec)
        output_body += sec
    return output_body


def comparable_ver(a: str):
    epoch_a, uv_a, dr_a = _break_down(a)
    return _comparable_digit(epoch_a) + '!' + _comparable_body(uv_a) + '!' + _comparable_body(dr_a)


def compare_ver(a: str, b: str):
    a = comparable_ver(a)
    b = comparable_ver(b)
    if a > b:
        return 1
    if a == b:
        return 0
    if a < b:
        return -1


cmp = lambda a, b: ((a > b) - (a < b))

def version_compare(a, b):
    def _order(x):
        """Return an integer value for character x"""
        if x == '~':
            return -1
        elif RE_DIGITS.match(x):
            return int(x) + 1
        elif RE_ALPHA.match(x):
            return ord(x)
        else:
            return ord(x) + 256

    def _version_cmp_string(va, vb):
        la = [_order(x) for x in va]
        lb = [_order(x) for x in vb]
        while la or lb:
            a = b = 0
            if la:
                a = la.pop(0)
            if lb:
                b = lb.pop(0)
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0

    def _version_cmp_part(va, vb):
        la = RE_ALL_DIGITS_OR_NOT.findall(va)
        lb = RE_ALL_DIGITS_OR_NOT.findall(vb)
        while la or lb:
            a = b = "0"
            if la:
                a = la.pop(0)
            if lb:
                b = lb.pop(0)
            if RE_DIGITS.match(a) and RE_DIGITS.match(b):
                a = int(a)
                b = int(b)
                if a < b:
                    return -1
                elif a > b:
                    return 1
            else:
                res = _version_cmp_string(a, b)
                if res != 0:
                    return res
        return 0

    return _version_cmp_part(a, b) or cmp(a, b)


def dpkg_version_compare(a, b):
    def _dpkg_version_split(v):
        epochpart = v.split(':', 1)
        if len(epochpart) == 1:
            epoch = 0
        else:
            epoch = int(epochpart[0])
        revpart = epochpart[-1].rsplit('-', 1)
        if len(revpart) == 1:
            rev = '0'
        else:
            rev = revpart[-1]
        return epoch, revpart[0], rev

    ae, av, ar = _dpkg_version_split(a)
    be, bv, br = _dpkg_version_split(b)
    if ae != be:
        return cmp(ae, be)
    elif av != bv:
        return version_compare(av, bv)
    res = version_compare(ar, br)
    if res:
        return res
    return cmp(a, b)
