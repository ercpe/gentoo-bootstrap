# -*- coding: utf-8 -*-
import logging
import os
from sh import Command


class StorageBase(object):

	def __init__(self, **kwargs):
		for k, v in kwargs.items():
			setattr(self, k, v)

	def create(self):
		raise NotImplementedError()

	def exists(self):
		e = os.path.exists(self.device)

		if e:
			logging.error("Device '%s' exists" % self.device)
		else:
			logging.debug("Does not exist: %s" % self.device)

		return e

	def format(self):
		cmd = None

		if self.filesystem == "swap":
			cmd = Command("mkswap")
		else:
			cmd = Command("mkfs.%s" % self.filesystem)

		logging.info("Formatting %s using %s" % (self.device, cmd))
		if self.opts:
			logging.debug("Formatting with opts: %s" % self.opts)
			cmd(self.device, self.opts)
		else:
			cmd(self.device)

	def is_block_storage(self):
		return True