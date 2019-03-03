CREATE OR REPLACE FUNCTION public._comparable_digit (digit text)
RETURNS text AS $$
  SELECT chr(47 + length(v)) || v
  FROM (SELECT CASE WHEN v='' THEN '0' ELSE v END v
    FROM (SELECT trim(leading '0' from digit) v) q1
  ) q2
$$ LANGUAGE SQL IMMUTABLE STRICT PARALLEL SAFE;

CREATE OR REPLACE FUNCTION public.comparable_ver (ver text)
RETURNS text AS $$
  WITH RECURSIVE q1 AS (
    SELECT regexp_match($1, '^([^0-9]*)([0-9]*)(.*)$') v
    UNION ALL
    SELECT regexp_match(v[3], '^([^0-9]*)([0-9]*)(.*)$') FROM q1
    WHERE v[3]!='' OR v[2]!=''
  )
  SELECT string_agg(translate(v[1] || '|',
    '~|ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-.',
    '0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefgh') ||
    (CASE WHEN v[2]='' THEN '' ELSE _comparable_digit(v[2]) END), '')
  FROM q1
$$ LANGUAGE SQL IMMUTABLE STRICT PARALLEL SAFE COST 200;

CREATE OR REPLACE FUNCTION public.comparable_dpkgver (ver text)
RETURNS text AS $$
  SELECT ecmp || '!' || (CASE WHEN array_length(spl, 1)=1
    THEN comparable_ver(spl[1]) || '!1'
    ELSE comparable_ver(array_to_string(spl[1:array_length(spl, 1)-1], '-'))
    || '!' || comparable_ver(spl[array_length(spl, 1)]) END)
  FROM (
    SELECT (CASE WHEN epos=0 THEN '00'
      ELSE _comparable_digit(substr(v, 1, epos-1)) END) ecmp, string_to_array(
      CASE WHEN epos=0 THEN v ELSE substr(v, epos+1) END, '-') spl
    FROM (SELECT position(':' in ver) epos, ver v) q1
  ) q1
$$ LANGUAGE SQL IMMUTABLE STRICT PARALLEL SAFE COST 200;
