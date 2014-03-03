# -*- coding: utf-8 -*-
import logging
import os
from gentoobootstrap.actions.base import ActionBase


class CreateDomUConfig(ActionBase):

	def __init__(self, config):
		super(CreateDomUConfig, self).__init__(config)
		self.domu_config = os.path.join('/etc/xen/', '%s.cfg' % self.config.name)

	def check(self):
		return not os.path.exists(self.domu_config)

	def execute(self):
		pass
# 		logging.info("Writing domU config...")
# 		cfg="""kernel = "{kernel_image}"
# vcpus  = {vcpu}
# memory = {memory}
# name   = "{name}"
# disk   = [ 'phy:{root_dev},xvda1,w' ]
# root   = "/dev/xvda1"
# vif    = [ 'mac={mac},bridge={bridge}', ]
# """
# 		with open(domU_config, 'w') as o:
# 			o.write(cfg.format(kernel_image=kernel_image, name=name, mac=mac, root_dev=lv_device))