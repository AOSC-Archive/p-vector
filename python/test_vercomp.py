#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import internal_dpkg_version
import string
import unittest
import hypothesis
from hypothesis.strategies import text

import psycopg2

class TestVercomp(unittest.TestCase):
    cmpmap = {'<': -1, '==': 0, '>': 1}

    def setUp(self):
        self.db = psycopg2.connect('dbname=texp')

    def _test_comparison(self, v1, cmp_oper, v2):
        self.assertEqual(
            internal_dpkg_version.dpkg_version_compare(v1, v2),
            self.cmpmap[cmp_oper])
        self.assertEqual(
            internal_dpkg_version.compare_ver(v1, v2),
            self.cmpmap[cmp_oper])

    def test_comparisons(self):
        """Test comparison against all combinations of Version classes"""

        self._test_comparison('0', '<', 'a')
        self._test_comparison('1.0', '<', '1.1')
        self._test_comparison('1.2', '<', '1.11')
        self._test_comparison('1.0-0.1', '<', '1.1')
        self._test_comparison('1.0-0.1', '<', '1.0-1')
        # make them different for sorting
        self._test_comparison('1:1.0-0', '>', '1:1.0')
        self._test_comparison('1.0', '==', '1.0')
        self._test_comparison('1.0-0.1', '==', '1.0-0.1')
        self._test_comparison('1:1.0-0.1', '==', '1:1.0-0.1')
        self._test_comparison('1:1.0', '==', '1:1.0')
        self._test_comparison('1.0-0.1', '<', '1.0-1')
        self._test_comparison('1.0final-5sarge1', '>', '1.0final-5')
        self._test_comparison('1.0final-5', '>', '1.0a7-2')
        self._test_comparison('0.9.2-5', '<',
                              '0.9.2+cvs.1.0.dev.2004.07.28-1.5')
        self._test_comparison('1:500', '<', '1:5000')
        self._test_comparison('100:500', '>', '11:5000')
        self._test_comparison('1.0.4-2', '>', '1.0pre7-2')
        self._test_comparison('1.5~rc1', '<', '1.5')
        self._test_comparison('1.5~rc1', '<', '1.5+b1')
        self._test_comparison('1.5~rc1', '<', '1.5~rc2')
        self._test_comparison('1.5~rc1', '>', '1.5~dev0')

    @hypothesis.given(text(string.ascii_letters + string.digits + '.+-~'))
    def test_comparable_ver(self, x):
        hypothesis.assume(x)
        internal_dpkg_version.comparable_ver(x)

    def test_comparable_ver_sql(self):
        versions = ['1:1.0-0.1', '20060611-0.0', '1:5000', '1.0final-5', 
            '4.2.0a+stable-2sarge1', '0.52.2-5.1', '1.8RC4b', '1.0-0.1', '1.5', 
            '1.5~dev0', '1.1.0+cvs20060620-1+1.0', 
            '0.9.2+cvs.1.0.dev.2004.07.28-1.5', '1.5~rc2', '10.11.1.3-2', 
            '11:5000', '0.2.0-1+b1', '1.1.0+cvs20060620-1+2.6.15-8', '100:500', 
            '1.0pre7-2', '1.5~rc1', '0.9.2-5', '1:1.0', 'a', '7.0-035+1', '1.5+b1', 
            '1.0a7-2', '1:1.8.8-070403-1~priv1', '1.1', '0', '1.0final-5sarge1', 
            '1.0.4-2', '7.1.ds-1', '4.3.90.1svn-r21976-1', '0.9~rc1-1', '1.2', 
            '4.0.1.3.dfsg.1-2', '1:1.0-0', '1.0-1', '1:1.4.1-1', '1:500', 
            '1.2.10+cvs20060429-1', '1.5+E-14', '1.0', '2:1.0.4~rc2-1', 
            '2:1.0.4+svn26-1ubuntu1', '0.4.23debian1', '1.11']
        cur = self.db.cursor()
        cur.execute("SELECT 'comparable_dpkgver'::regproc")
        for version in versions:
            cur.execute("SELECT comparable_dpkgver(%s)", (version,))
            self.assertEqual(cur.fetchone()[0],
                internal_dpkg_version.comparable_ver(version), version)

if __name__ == '__main__':
    unittest.main()
