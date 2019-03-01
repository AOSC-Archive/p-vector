BEGIN;

DELETE FROM pv_package_issues WHERE id IN (
  SELECT i.id FROM pv_package_issues i
  LEFT JOIN pv_packages p USING (package, version, repo)
  WHERE p.package IS NULL
);

CREATE TEMP VIEW tv_updated AS
SELECT coalesce(extract(epoch from max(atime)), 0)::integer t
FROM pv_package_issues;

CREATE TEMP VIEW tv_pv_packages AS
SELECT * FROM pv_packages WHERE mtime >= (SELECT t FROM tv_updated);
CREATE TEMP VIEW tv_packages_new AS
SELECT * FROM v_packages_new WHERE mtime >= (SELECT t FROM tv_updated);

CREATE TEMP TABLE t_package_issues AS
----- 101 -----
SELECT r.package, ((CASE WHEN coalesce(r.epoch, '') = '' THEN ''
    ELSE r.epoch || ':' END) || r.version ||
   (CASE WHEN coalesce(r.release, '') IN ('', '0') THEN ''
    ELSE '-' || r.release END)) "version", t.name || '/' || v.branch repo,
  101::int errno, 0::smallint "level", e.filename,
  jsonb_build_object('err', e.err, 'githash', m.githash) detail
FROM repo_package_basherr e
INNER JOIN repo_package_rel r USING (tree, rid)
INNER JOIN repo_marks m USING (tree, rid)
INNER JOIN trees t ON t.tid=m.tree
INNER JOIN package_versions v
ON v.package=r.package AND v.githash=m.githash
AND v.version IS NOT DISTINCT FROM r.version
AND v.release IS NOT DISTINCT FROM r.release
AND v.epoch IS NOT DISTINCT FROM r.epoch
INNER JOIN packages p ON p.name=r.package
AND p.category IS NOT DISTINCT FROM e.category
AND p.section=e.section AND p.directory=e.directory
WHERE e.package IS NULL
UNION ALL ----- 102 -----
SELECT r.package, ((CASE WHEN coalesce(r.epoch, '') = '' THEN ''
    ELSE r.epoch || ':' END) || r.version ||
   (CASE WHEN coalesce(r.release, '') IN ('', '0') THEN ''
    ELSE '-' || r.release END)) "version", t.name || '/' || v.branch repo,
  102::int errno, 0::smallint "level", e.filename,
  jsonb_build_object('err', e.err, 'githash', m.githash) detail
FROM repo_package_basherr e
INNER JOIN repo_package_rel r USING (tree, rid, package)
INNER JOIN repo_marks m USING (tree, rid)
INNER JOIN trees t ON t.tid=m.tree
INNER JOIN package_versions v
ON v.package=r.package AND v.githash=m.githash
AND v.version IS NOT DISTINCT FROM r.version
AND v.release IS NOT DISTINCT FROM r.release
AND v.epoch IS NOT DISTINCT FROM r.epoch
WHERE e.package IS NOT NULL
UNION ALL ----- 301 -----
SELECT package, version, repo, 301::int errno, 0::smallint "level",
  filename, jsonb_build_object('size', size) detail
FROM tv_pv_packages WHERE debtime IS NULL
UNION ALL ----- 302 -----
SELECT p.package, version, repo, 302::int errno, 0::smallint "level", filename,
  jsonb_build_object('size', p.size, 'medsize', q1.medsize) detail
FROM tv_packages_new p
INNER JOIN (
  SELECT package, percentile_cont(0.5) WITHIN GROUP (ORDER BY size) medsize
  FROM tv_pv_packages WHERE debtime IS NOT NULL GROUP BY package
) q1 ON p.package=q1.package AND p.size < q1.medsize/2
WHERE p.debtime IS NOT NULL
UNION ALL ----- 303 -----
SELECT p.package, p.version, p.repo, 303::int errno, 0::smallint "level",
  p.filename, null::jsonb detail
FROM tv_pv_packages p
INNER JOIN pv_repos r ON r.name=p.repo
WHERE p.filename NOT LIKE array_to_string(ARRAY['pool', r.path,
  CASE WHEN p.package LIKE 'lib%' THEN substring(p.package from 1 for 4)
  ELSE substring(p.package from 1 for 1) END, '%'], '/')
UNION ALL ----- 311 -----
SELECT package, version, repo, 311::int errno, 0::smallint "level",
  filename, jsonb_object(ARRAY['maintainer', maintainer]) detail
FROM tv_packages_new
WHERE maintainer !~ '^.+ <.+@.+>$'
OR maintainer='Null Packager <null@aosc.xyz>'
UNION ALL ----- 321 -----
SELECT f.package, f.version, f.repo, 321::int errno, 0::smallint "level",
  '/' || path || '/' || name filename,
  jsonb_build_object('size', size, 'perm', perm, 'uid', uid, 'gid', gid,
    'uname', uname, 'gname', gname) detail
FROM pv_package_files f
WHERE package!='aosc-aaa' AND ftype='reg' AND (path='usr/local' OR
  path !~ '^(bin|boot|etc|lib|opt|run|sbin|srv|usr|var)/?.*')
UNION ALL ----- 322 -----
SELECT f.package, f.version, f.repo, 322::int errno,
  (1-(perm&1))::smallint "level", '/' || path || '/' || name filename,
  jsonb_build_object('size', f.size, 'perm', f.perm, 'uid', f.uid, 'gid', f.gid,
    'uname', f.uname, 'gname', f.gname) detail
FROM pv_package_files f
INNER JOIN tv_packages_new USING (package, version, repo)
WHERE f.size=0 AND ftype='reg' AND perm & 1=1
AND name NOT IN ('NEWS', 'ChangeLog', 'INSTALL', 'TODO', 'COPYING', 'AUTHORS',
  'README', 'README.md', 'README.txt', 'empty', 'placeholder', 'placeholder.txt')
AND name NOT LIKE '.%' AND name NOT LIKE '__init__.p%'
UNION ALL ----- 323 -----
SELECT f.package, f.version, f.repo, 323::int errno,
  -(perm&1)::smallint "level", '/' || path || '/' || name filename,
  jsonb_build_object('size', f.size, 'perm', f.perm, 'uid', f.uid, 'gid', f.gid,
    'uname', f.uname, 'gname', f.gname) detail
FROM pv_package_files f
INNER JOIN tv_packages_new USING (package, version, repo)
WHERE uid>999 OR gid>999
UNION ALL ----- 324 -----
SELECT f.package, f.version, f.repo, 324::int errno,
  0::smallint "level", '/' || path || '/' || name filename,
  jsonb_build_object('size', f.size, 'perm', f.perm, 'uid', f.uid, 'gid', f.gid,
    'uname', f.uname, 'gname', f.gname) detail
FROM pv_package_files f
INNER JOIN tv_packages_new USING (package, version, repo)
WHERE (path IN ('bin', 'sbin', 'usr/bin') AND perm&1=0 AND ftype='reg')
OR (ftype='dir' AND perm&64=0)
UNION ALL ----- 402 -----
SELECT
  p.name package, ((CASE WHEN coalesce(pv.epoch, '') = '' THEN ''
    ELSE pv.epoch || ':' END) || pv.version ||
   (CASE WHEN coalesce(pv.release, '') IN ('', '0') THEN ''
    ELSE '-' || pv.release END)) "version", p.tree || '/' || pv.branch repo,
  402::int errno, min((p.tree!=d.tree)::int::smallint) "level",
  (p.tree || '/' || coalesce(p.category || '-' || p.section, p.section) ||
    '/' || p.directory) filename,
  jsonb_build_object('paths', jsonb_agg(d.tree || '/' || (CASE WHEN d.category=''
    THEN d.section ELSE d.category || '-' || d.section END) || '/' ||
    d.directory), 'githash', pv.githash) detail
FROM packages p
INNER JOIN package_duplicate d ON d.package=p.name
AND NOT (d.tree=p.tree AND d.category=coalesce(p.category, '')
  AND d.section=p.section AND d.directory=p.directory)
INNER JOIN trees t ON t.name=p.tree
INNER JOIN package_versions pv
ON pv.package = p.name AND pv.branch = t.mainbranch
GROUP BY p.name, pv.epoch, pv.version, pv.release, pv.branch, pv.githash,
  p.tree, p.category, p.section, p.directory
UNION ALL ----- 412 -----
SELECT
  d.package, d.version, d.repo, 412::int errno, 0::smallint "level",
  min(p.filename), jsonb_build_object('filenames',
    ARRAY[jsonb_agg(d.filename)]) detail
FROM pv_package_duplicate d
INNER JOIN tv_pv_packages p USING (package, version, repo)
GROUP BY d.package, d.version, d.repo
UNION ALL ----- 421 -----
SELECT
  package, version, repo, errno, "level", filename, detail
FROM (
  SELECT DISTINCT ON (package, version, repo, filename)
    f1.package, f1.version, f1.repo, 421::int errno, 0::smallint "level",
    '/' || f1.path || '/' || f1.name filename,
    jsonb_object('{repo, package, version}',
      ARRAY[f2.repo, f2.package, f2.version]) detail
  FROM pv_package_files f1
  INNER JOIN v_packages_new v1
  ON v1.package=f1.package AND v1.version=f1.version AND v1.repo=f1.repo
  INNER JOIN pv_repos r1 ON r1.name=v1.repo
  INNER JOIN pv_repos r2 ON r2.architecture IN (r1.architecture, 'all')
  AND r2.testing<=r1.testing AND r2.component=r1.component
  INNER JOIN v_packages_new v2
  ON v2.repo=r2.name AND v2.package!=v1.package
  INNER JOIN pv_package_files f2
  ON v2.package=f2.package AND v2.version=f2.version AND v2.repo=f2.repo
  AND f2.path=f1.path AND f2.name=f1.name
  LEFT JOIN v_dpkg_dependencies d1
  ON d1.package=f1.package AND d1.version=f1.version AND d1.repo=f1.repo
  AND d1.relationship IN ('Breaks', 'Replaces', 'Conflicts')
  AND d1.deppkg=v2.package AND (d1.deparch IS NULL OR d1.deparch=r2.architecture)
  AND (CASE WHEN d1.relop IS NULL THEN TRUE
    WHEN d1.relop='<<' THEN v2._vercomp < d1.depvercomp
    WHEN d1.relop='<=' THEN v2._vercomp <= d1.depvercomp
    WHEN d1.relop='=' THEN v2._vercomp = d1.depvercomp
    WHEN d1.relop='>=' THEN v2._vercomp >= d1.depvercomp
    WHEN d1.relop='>>' THEN v2._vercomp > d1.depvercomp END)
  LEFT JOIN v_dpkg_dependencies d2
  ON d2.package=v2.package AND d2.version=v2.version AND d2.repo=v2.repo
  AND d2.relationship IN ('Breaks', 'Replaces', 'Conflicts')
  AND d2.deppkg=f1.package AND (d2.deparch IS NULL OR d2.deparch=r1.architecture)
  AND (CASE WHEN d2.relop IS NULL THEN TRUE
    WHEN d2.relop='<<' THEN v1._vercomp < d2.depvercomp
    WHEN d2.relop='<=' THEN v1._vercomp <= d2.depvercomp
    WHEN d2.relop='=' THEN v1._vercomp = d2.depvercomp
    WHEN d2.relop='>=' THEN v1._vercomp >= d2.depvercomp
    WHEN d2.relop='>>' THEN v1._vercomp > d2.depvercomp END)
  WHERE f1.ftype='reg' AND d1.package IS NULL AND d2.package IS NULL
  AND (v1.mtime >= (SELECT t FROM tv_updated)
    OR v2.mtime >= (SELECT t FROM tv_updated))
  ORDER BY package, version, repo, filename, r2.testing DESC
) q2
UNION ALL ----- 431 -----
SELECT
  package, version, repo, 431::int errno, 0::smallint "level", filename, detail
FROM (
  SELECT DISTINCT ON (package, version, repo, filename)
    package, version, repo, (name || ver) filename, ver_provide,
    CASE WHEN package_lib IS NULL THEN NULL ELSE
      jsonb_object('{repo, package, version, sover_provide}',
      ARRAY[repo_lib, package_lib, version_lib, ver_provide]) END detail
  FROM (
    SELECT
      sd.package, sd.version, sd.repo, sd.name, rp.name repo_lib,
      sp.package package_lib, sp.version version_lib, sd.ver, sp.ver ver_provide,
      count(sp2.package) OVER w matchcnt
    FROM pv_package_sodep sd
    INNER JOIN tv_packages_new vp USING (package, version, repo)
    INNER JOIN pv_repos rd ON rd.name=sd.repo
    INNER JOIN pv_repos rp ON rd.architecture IN (rp.architecture, 'all')
    AND rp.testing<=rd.testing AND rp.component IN (rd.component, 'main')
    LEFT JOIN pv_package_sodep sp ON sp.repo=rp.name
    AND sp.depends=0 AND sd.name=sp.name
    LEFT JOIN v_packages_new vp2
    ON vp2.package=sp.package AND vp2.version=sp.version AND vp2.repo=sp.repo
    LEFT JOIN pv_package_sodep sp2
    ON sp2.repo=sp.repo AND sp2.package=sp.package AND sp2.version=sp.version
    AND sp.name=sp2.name AND sp.ver=sp2.ver AND sp2.depends=0
    AND (sp2.ver=sd.ver OR sp2.ver LIKE sd.ver || '.%')
    WHERE sd.depends=1 AND (sp.package IS NULL OR vp2.package IS NOT NULL)
    WINDOW w AS (PARTITION BY sd.package, sd.version, sd.repo, sd.name, sd.ver)
  ) q3
  WHERE matchcnt=0
  ORDER BY package, version, repo, filename, comparable_ver(ver_provide) DESC
) q4
;

UPDATE pv_package_issues SET atime=now()
WHERE id IN (
  SELECT i.id FROM pv_package_issues i
  INNER JOIN tv_pv_packages p USING (package, version, repo)
  UNION ALL
  SELECT i.id FROM pv_package_issues i WHERE errno < 200
);

WITH samerows AS (
  SELECT p.id
  FROM pv_package_issues p
  INNER JOIN t_package_issues t USING (
    package, version, repo, errno, "level", filename)
  WHERE p.detail IS NOT DISTINCT FROM t.detail
)
UPDATE pv_package_issues p
SET mtime=now(), "level"=t."level", detail=t.detail
FROM t_package_issues t
WHERE t.package=p.package AND t.version=p.version AND t.repo=p.repo
AND t.errno=p.errno AND t.filename=p.filename
AND p.id NOT IN (SELECT id FROM samerows);

INSERT INTO pv_package_issues
  (package, version, repo, errno, "level", filename, detail)
SELECT t.* FROM t_package_issues t
LEFT JOIN pv_package_issues p USING (package, version, repo, errno, filename)
WHERE p.package IS NULL;

DROP TABLE t_package_issues;

COMMIT;
