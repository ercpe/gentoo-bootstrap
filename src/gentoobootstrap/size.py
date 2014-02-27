# -*- coding: utf-8 -*-

import re


class Size(object):
	suffixes = ['k', 'm', 'g', 't']

	def __init__(self, size=0):
		if isinstance(size, (int, )):
			self.bytes = size
		elif isinstance(size, str):
			self.bytes = self.parse(size)
		elif isinstance(size, Size):
			self.bytes = size.bytes

		if self.bytes < 0:
			raise Exception("Size cannot be smaller than 0 bytes")

	def parse(self, s):
		m = re.match('^(\d+)\s*([kmgt]?)', s.strip(), re.IGNORECASE)

		if not m:
			raise Exception("Illegal size specification: %s" % s)

		suffix = m.group(2).lower() if m.group(2) else None
		if suffix and not suffix in self.suffixes:
			raise Exception("Illegal suffix: '%s'" % suffix)

		multi = 1
		if suffix:
			multi = 1024 ** (self.suffixes.index(suffix)+1)

		return int(m.group(1)) * multi

	def __str__(self):
		if not self.bytes:
			return str(self.bytes)

		for i, u in reversed(list(enumerate(self.suffixes))):
			x = float(self.bytes) / (1024 ** (i+1))
			if x == int(x):
				return "%s%s" % (int(x), u.upper())

		return str(self.bytes)