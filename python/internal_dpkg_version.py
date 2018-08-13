import re

_partitions = re.compile(r'^((?P<epoch>[0-9]+):)?(?P<body>[A-Za-z0-9.+~-]+)$')
_non_digit = re.compile(r'^[A-Za-z.+~-]*')
_digit = re.compile(r'^[0-9]*')


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
    return chr(ord('a') + (length - 1)) + clean_number


def _comparable_non_digit(s: str):
    # Add '|' to indicate the end of string
    s = (s + '|').encode('ASCII')

    def m(n):
        if n == ord('|'):
            return ord('%')  # Let the end of string be 1
        if n == ord('~'):
            return ord('#')  # '~' should be even less than the end of string
        return n

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
