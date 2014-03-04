# -*- coding: utf-8 -*-
import logging
import os
from gentoobootstrap.actions.base import ActionBase


class CreateDomUConfig(ActionBase):

	def __init__(self, config):
		super(CreateDomUConfig, self).__init__(config)
		self.domu_config = os.path.join('/etc/xen/', '%s.cfg' % self.config.name)

	def test(self):
		e = os.path.exists(self.domu_config)
		if e:
			logging.error("domU config %s already exists" % self.domu_config)
		return not e

	def execute(self):
		logging.info("Writing domU config...")

		storage_devices = []
		for storage, mount in self.config.storage:
			storage_devices.append("'phy:%s,%s,w'" % (storage.device, storage.domu_device))

		cfg="""kernel = "{kernel_image}"
vcpus  = {vcpu}
memory = {memory}
name   = "{name}"
disk   = [ {storage} ]
root   = "/dev/xvda1"
vif    = [ 'mac={mac},bridge={bridge}', ]
""".format(name=self.config.name, vcpu=self.config.vcpu, memory=self.config.memory,
		mac=self.config.mac_address, bridge=self.config.network[0], storage=', '.join(storage_devices),
		kernel_image=self.config.kernel)

		with open(self.domu_config, 'w') as o:
			o.write(cfg)