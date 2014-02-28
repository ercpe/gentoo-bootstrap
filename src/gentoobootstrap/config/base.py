# -*- coding: utf-8 -*-
import random
import tempfile


class ConfigBase(object):

	def __init__(self, **kwargs):
		self._working_directory = None
		self._mac = None
		self.name = kwargs.get('name')

	@property
	def working_directory(self):
		if not self._working_directory:
			self._working_directory = tempfile.mkdtemp()
		return self._working_directory

	@property
	def mac_address(self):
		if not self._mac:
			self._mac = ':'.join(map(lambda x: "%02x" % x, [0x00, 0x16, 0x3e,
								random.randint(0x00, 0x7f),
								random.randint(0x00, 0xff),
								random.randint(0x00, 0xff)]))
		return self._mac