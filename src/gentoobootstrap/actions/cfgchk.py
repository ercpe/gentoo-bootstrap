# -*- coding: utf-8 -*-
import logging
import re
from configparser import NoOptionError
from gentoobootstrap.actions.base import ActionBase


class CheckConfigAction(ActionBase):
	"""
	Action to test for configuration errors. This class does not implement the .execute() method as it is
	a test-only action
	"""

	def test(self):
		if not re.match("^[\w\d_-]+$", self.config.name, re.IGNORECASE):
			logging.error("The domU name must not contain characters beside a-Z0-9_-.")
			return False

		for attr_name in dir(self.config):
			if attr_name.startswith('_'):
				continue

			try:
				getattr(self.config, attr_name)
			except NoOptionError:
				logging.error("Attribute '%s' not defined in configuration" % attr_name)
				return False

		return True
