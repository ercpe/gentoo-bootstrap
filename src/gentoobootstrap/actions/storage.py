# -*- coding: utf-8 -*-
import logging
from gentoobootstrap.actions.base import ActionBase


class CreateStorageAction(ActionBase):

	def test(self):
		return self.config.has_storage and all([not storage.exists() for storage, mount in self.config.storage])

	def execute(self):
		logging.info("Creating storage...")
		for storage, mount in self.config.storage:
			storage.create()
			storage.format()
