# -*- coding: utf-8 -*-
import logging
import os
from cfgio.specialized.xen import XenConfig, XenDomUVifConfigValue, XenDomUDiskConfigValue
from gentoobootstrap.actions.base import ActionBase


class CreateDomUConfig(ActionBase):

	def __init__(self, config):
		super(CreateDomUConfig, self).__init__(config)
		self.domu_config = os.path.join(self.config.xen_config_dir, '%s.cfg' % self.config.name)
		logging.debug("domU configuration file: %s" % self.domu_config)

	def test(self):
		e = os.path.exists(self.domu_config)
		if e:
			logging.error("domU config %s already exists" % self.domu_config)
		return not e

	def execute(self):
		logging.info("Writing domU config...")

		with XenConfig(self.domu_config) as cfg:
			cfg.set('name', self.config.name)
			cfg.set('kernel', self.config.kernel)
			cfg.set('vcpus', self.config.vcpu)
			cfg.set('memory', self.config.memory)
			cfg.set('disk', [
				XenDomUDiskConfigValue("phy", storage.device, os.path.basename(storage.domu_device), 'rw') for storage, mount in self.config.storage
			])
			cfg.set('root', self.config.root_storage.domu_device)
			cfg.set('vif', [ XenDomUVifConfigValue(mac=self.config.mac_address, bridge=self.config.network[0]) ])
