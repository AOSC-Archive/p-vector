from pymongo.collection import Collection

SQL_CHECK_SOVER = """
SELECT
  package, version, repo, name, repo_lib, package_lib, version_lib, ver, ver_provide
FROM (
  SELECT
    sd.package, sd.version, sd.repo, sd.name, rp.name repo_lib,
    sp.package package_lib, sp.version version_lib, sd.ver, sp.ver ver_provide,
    count(sp2.package) OVER w matchcnt
  FROM pv_package_sodep sd
  INNER JOIN v_packages_new vp USING (package, version, repo)
  INNER JOIN pv_repos rd ON rd.name=sd.repo
  INNER JOIN pv_repos rp ON rp.architecture=rd.architecture
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
) q1
WHERE matchcnt=0
"""

SQL_CHECK_CONFLICT = """
SELECT
  f1.package package1, f1.version version1, f1.repo repo1,
  f2.package package2, f2.version version2, f2.repo repo2,
  f1.path || '/' || f1.name filename
FROM pv_package_files f1
INNER JOIN pv_repos r1 ON r1.name=f1.repo
INNER JOIN pv_repos r2 ON r2.architecture IN (r1.architecture, 'all')
AND r2.testing<=r1.testing AND r2.component=r1.component
INNER JOIN v_packages_new v2
ON v2.repo=r2.name AND v2.package!=f1.package
INNER JOIN pv_package_files f2
ON v2.package=f2.package AND v2.version=f2.version AND v2.repo=f2.repo
AND f2.path=f1.path AND f2.name=f1.name
LEFT JOIN v_dpkg_dependencies d1
ON d1.package=f1.package AND d1.version=f1.version AND d1.repo=f1.repo
AND d1.relationship IN ('Breaks', 'Replaces', 'Conflicts')
AND d1.deppkg=v2.package AND (d1.deparch IS NULL OR d1.deparch=r2.architecture)
AND (CASE WHEN relop IS NULL THEN TRUE
  WHEN relop='<<' THEN v2._vercomp < d1.depvercomp
  WHEN relop='<=' THEN v2._vercomp <= d1.depvercomp
  WHEN relop='=' THEN v2._vercomp = d1.depvercomp
  WHEN relop='>=' THEN v2._vercomp >= d1.depvercomp
  WHEN relop='>>' THEN v2._vercomp > d1.depvercomp END)
WHERE f1.ftype='reg' AND d1.package IS NULL
"""

aggregate_args = [
    {'$facet': {
        'depends': [
            {'$project': {'so_depends': 1}},
            {'$unwind': '$so_depends'},
            {'$group': {'_id': '$so_depends'}}
        ],
        'provides': [
            {'$project': {'so_provides': 1}},
            {'$unwind': '$so_provides'},
            {'$group': {'_id': '$so_provides'}}
        ]
    }},
    {'$project': {
        'not_matched_name': {'$setDifference': ['$depends._id.name', '$provides._id.name']},
        'matched_name': {'$setIntersection': ['$depends._id.name', '$provides._id.name']},
        'not_perfect_matched_depends': {'$setDifference': ['$depends._id', '$provides._id']},
        'provides': '$provides._id'
    }},
    {'$project': {
        'name_not_matched_depends': {
            '$filter': {
                'input': '$not_perfect_matched_depends',
                'cond': {'$in': ['$$this.name', '$not_matched_name']}
            }
        },
        'only_name_matched_depends': {
            '$filter': {
                'input': '$not_perfect_matched_depends',
                'cond': {'$in': ['$$this.name', '$matched_name']}
            }
        },
        'probable_provides': {
            '$filter': {
                'input': '$provides',
                'cond': {'$in': ['$$this.name', '$matched_name']}
            }
        },
    }},
    {'$project': {
        'resolved_0_depends': {
            '$filter': {
                'input': {
                    '$map': {
                        'input': '$only_name_matched_depends',
                        'in': {
                            'test': {
                                'name': '$$this.name',
                                'ver': {'$concat': ['$$this.ver', '.0']}
                            },
                            'origin': '$$this'
                        }
                    }
                },
                'cond': {
                    '$in': ['$$this.test', '$probable_provides']
                }
            }
        },
        'resolved_00_depends': {
            '$filter': {
                'input': {
                    '$map': {
                        'input': '$only_name_matched_depends',
                        'in': {
                            'test': {
                                'name': '$$this.name',
                                'ver': {'$concat': ['$$this.ver', '.0.0']}
                            },
                            'origin': '$$this'
                        }
                    }
                },
                'cond': {
                    '$in': ['$$this.test', '$probable_provides']
                }
            }
        },
        'name_not_matched_depends': 1,
        'only_name_matched_depends': 1,
        'probable_provides': 1
    }},
    {'$project': {
        'missing_soname_depends': '$name_not_matched_depends',
        'not_sure_depends': {
            '$setDifference': [{'$setDifference': ['$only_name_matched_depends', '$resolved_00_depends.origin']},
                               '$resolved_0_depends.origin']},
        'probable_provides': 1
    }},
    {'$project': {
        'missing_soname_depends': 1,
        'not_sure_depends': 1,
        'probable_provides': 1,
        'matched_name': {'$setIntersection': ['$not_sure_depends.name', '$probable_provides.name']},
    }},
    {'$project': {
        'missing_soname_depends': 1,
        'not_sure_depends': 1,
        'probable_provides': {
            '$filter': {
                'input': '$probable_provides',
                'cond': {'$in': ['$$this.name', '$matched_name']}
            }
        },
    }}]


def match_sover(want: str, have: str):
    return (have + '.').startswith(want + '.')


def check(pkg_col: Collection):
    r = pkg_col.aggregate(aggregate_args).next()
    print_missing_name(pkg_col, r['missing_soname_depends'])

    missing_version_depends = []
    provides_cache = dict()
    for i in r['probable_provides']:
        if i['name'] not in provides_cache:
            provides_cache[i['name']] = []
        provides_cache[i['name']].append(i['ver'])

    for i in r['not_sure_depends']:
        found = False
        for j in provides_cache[i['name']]:
            if match_sover(want=i['ver'], have=j):
                found = True
                break
        if not found:
            missing_version_depends.append(i)
    print_missing(pkg_col, missing_version_depends)


def print_missing_name(pkg_col: Collection, missing):
    missing_name = []
    for i in missing:
        missing_name.append(i['name'])

    print(pkg_col.name)
    cur = pkg_col.aggregate([
        {'$match': {'so_depends': {'$in': missing}}},
        {'$project': {'_id': 0, 'pkg': 1, 'so_depends': 1}},
        {'$unwind': '$so_depends'},
        {'$match': {'so_depends': {'$in': missing}}},
        {'$group': {'_id': {'$concat': ['$pkg.name', '(', '$pkg.ver', ')']},
                    'so_depends': {'$addToSet': '$so_depends'}}}
    ])

    c = [i for i in cur]
    print(len(c))
    c.sort(key=lambda x: x['_id'])
    for i in c:
        pkg = i['_id']
        broken = i['so_depends']

        broken = [b['name'] + b['ver'] for b in broken]
        broken.sort()
        print(pkg + ':', ', '.join(broken))


def print_missing(pkg_col: Collection, missing):
    missing_name = []
    for i in missing:
        missing_name.append(i['name'])

    print(pkg_col.name)
    cur = pkg_col.aggregate([
        {'$match': {'so_depends': {'$in': missing}}},
        {'$project': {'_id': 0, 'pkg': 1, 'so_depends': 1}},
        {'$unwind': '$so_depends'},
        {'$match': {'so_depends': {'$in': missing}}},
        {'$lookup': {
            'from': pkg_col.name,
            'localField': 'so_depends.name',
            'foreignField': 'so_provides.name',
            'as': 'probably'
        }},
        {'$project': {'pkg': 1, 'so_depends': 1, 'probably.pkg': 1, 'probably.so_provides': 1}},
        {'$unwind': '$probably'},
        {'$unwind': '$probably.so_provides'},
        {'$match': {'probably.so_provides.name': {'$in': missing_name}}},
        {'$group': {
            '_id': {'$concat': ['$pkg.name', '(', '$pkg.ver', ')']},
            'broken_dep': {'$addToSet': '$so_depends'},
            'probably': {
                '$addToSet': {
                    'pkg': {'$concat': ['$probably.pkg.name', '(', '$probably.pkg.ver', ')']},
                    'so_provides': '$probably.so_provides'
                }
            },
        }},
    ])

    c = [i for i in cur]
    print(len(c))
    c.sort(key=lambda x: x['_id'])
    for i in c:
        pkg = i['_id']
        broken = i['broken_dep']
        probably = {}
        for p in i['probably']:
            for d in broken:
                if p['so_provides']['name'] == d['name']:
                    if p['pkg'] not in probably:
                        probably[p['pkg']] = []
                    probably[p['pkg']].append(p['so_provides']['name'] + p['so_provides']['ver'])
                    break
        print(pkg + ':')

        broken = [b['name'] + b['ver'] for b in broken]
        broken.sort()
        print('  missing:', ', '.join(broken))

        if len(probably) != 0:
            print('  hints:')
            for p in probably:
                probably[p].sort()
                print('    - ' + p + ' has ' + ', '.join(probably[p]))
        print()
