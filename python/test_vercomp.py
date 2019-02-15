#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import internal_dpkg_version
import string
import unittest
import hypothesis
from hypothesis.strategies import text


class TestVercomp(unittest.TestCase):
    cmpmap = {'<': -1, '==': 0, '>': 1}

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

if __name__ == '__main__':
    unittest.main()
