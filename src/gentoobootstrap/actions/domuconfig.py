# -*- coding: utf-8 -*-
import os
from gentoobootstrap.actions.base import ActionBase


class CreateDomUConfig(ActionBase):

	def __init__(self, config):
		super(CreateDomUConfig, self).__init__(config)
		self.domu_config = os.path.join('/etc/xen/', '%s.cfg' % self.config.name)

	def check(self):
		return not os.path.exists(self.domu_config)
