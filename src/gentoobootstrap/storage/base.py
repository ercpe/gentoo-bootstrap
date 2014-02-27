# -*- coding: utf-8 -*-
import logging
import os
from sh import Command


class StorageBase(object):

	def __init__(self, size, name, device, filesystem):
		self.size = size
		self.name = name
		self.device = device
		self.filesystem = filesystem

	def create(self):
		pass

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
		cmd(self.device)

	def __repr__(self):
		return "%s (%s), type %s" % (self.name, self.size, self.filesystem)