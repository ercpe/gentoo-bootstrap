# -*- coding: utf-8 -*-
import os
from gentoobootstrap.size import Size

from gentoobootstrap.storage.base import StorageBase
import logging
from sh import lvcreate

class LVMStorage(StorageBase):

	def __init__(self, **kwargs):
		super(LVMStorage, self).__init__(**kwargs)
		self.volume_group = kwargs.pop('volume_group')
		self.size = Size(self.size)
		self.device = os.path.join("/dev", self.volume_group, self.name)

	def create(self):
		logging.info("Creating the LV '%s' with %s on volume group %s" % (self.name, self.size, self.volume_group))
		for line in lvcreate("-L", str(self.size), "-d", "-n", self.name, self.volume_group, _in="y"):
			logging.info(line)

	def __repr__(self):
		return "%s (%s), type %s" % (self.name, self.size, self.fs)