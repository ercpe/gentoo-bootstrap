# -*- coding: utf-8 -*-
import os

from gentoobootstrap.storage.base import StorageBase
import logging
from sh import lvcreate

class LVMStorage(StorageBase):

	def __init__(self, size, name, domu_device, filesystem, **kwargs):
		self.volume_group = kwargs.pop('volume_group')
		super(LVMStorage, self).__init__(size, name, os.path.join("/dev", self.volume_group, name), domu_device, filesystem, **kwargs)

	def create(self):
		logging.info("Creating the LV '%s' with %s on volume group %s" % (self.name, self.size, self.volume_group))
		lvcreate("-L", str(self.size), "-n", self.name, self.volume_group)
