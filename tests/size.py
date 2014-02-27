# -*- coding: utf-8 -*-

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../src/'))

from gentoobootstrap.size import Size


class TestSizes(object):

	def test_calculation(self):
		l = [
			(1, 1),
			(1024, 1024),
			('1k', 1024),
			('2k', 2048),
			('1M', 1024*1024),
			('1G', 1024*1024*1024),
			('1T', 1024*1024*1024*1024)
		]
		for s, expected in l:
			assert Size(s).bytes == expected

		# numeric arguments must result in the same number of bytes
		# as a suffixed argument
		assert Size(1024).bytes == Size('1k').bytes

	def test_units(self):
		# we don't care about lower/upper-case units
		for x in ['k', 'm', 'g', 't']:
			assert Size('1%s' % x).bytes == Size('1%s' % x.upper()).bytes

	def test_str(self):
		for u in ['k', 'm', 'g', 't']:
			assert str(Size("1%s" % u)) == "1%s" % u.upper()
