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
		lvcreate("-L", str(self.size), "-n", self.name, self.volume_group)

	def __repr__(self):
		return "%s (%s), type %s" % (self.name, self.size, self.filesystem)