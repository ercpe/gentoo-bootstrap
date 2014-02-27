# -*- coding: utf-8 -*-
import os

from gentoobootstrap.storage.base import StorageBase
import logging
from sh import lvcreate

class LVMStorage(StorageBase):

	def __init__(self, size, name, filesystem, **kwargs):
		self.volume_group = kwargs.get('volume_group')
		super(LVMStorage, self).__init__(size, name, os.path.join("/dev", self.volume_group, name), filesystem)

	def create(self):
		logging.info("Creating the LV '%s' with %s on volume group %s" % (self.name, self.size, self.volume_group))
		lvcreate("-L", str(self.size), "-n", self.name, self.volume_group)
