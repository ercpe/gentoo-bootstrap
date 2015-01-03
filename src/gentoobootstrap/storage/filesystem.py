# -*- coding: utf-8 -*-
import logging
import os
from gentoobootstrap.storage.base import StorageBase


class FilesystemStorage(StorageBase):

	def create(self):
		if not os.path.exists(self.device):
			os.makedirs(self.device, mode=0o700)

	def format(self):
		pass

	def exists(self):
		x = os.path.exists(self.device) and len(os.listdir(self.device)) > 0
		if x:
			logging.error("%s exists and is not empty" % self.device)
		return x

	def is_block_storage(self):
		return False

	def __repr__(self):
		return "Filesystem (%s)" % self.device