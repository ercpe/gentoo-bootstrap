# -*- coding: utf-8 -*-

from configparser import ConfigParser
from gentoobootstrap.config import DIST_CFG_DIR, SITE_CFG_DIR
from gentoobootstrap.config.base import ConfigBase
import logging
import os
from gentoobootstrap.size import Size
from gentoobootstrap.storage import get_impl as get_storage_impl


class FileConfig(ConfigBase):

	def __init__(self, file, **kwargs):
		self.name = kwargs.get('name')
		file = os.path.abspath(file)
		self.parser = ConfigParser(defaults=kwargs)
		files_read = self.parser.read([os.path.abspath(os.path.join(DIST_CFG_DIR, 'dist.cfg')),
										os.path.abspath(os.path.join(SITE_CFG_DIR, 'site.cfg')),
										file])
		logging.info("Read configuration files: %s" % ','.join(files_read))

		if not file in files_read:
			logging.warning("Your configuration in %s has been ignored!" % file)

	def _make_list(self, value):
		return [x.strip() for x in value.split(',')]

	def _get_value(self, section, option, default=None):
		return self.parser.get(section, option) \
				if self.parser.has_option(section, option) \
				else default

	@property
	def arch(self):
		return self.parser.get('system', 'arch')

	@property
	def locales(self):
		return self._make_list(self._get_value('system', 'locales', ''))

	@property
	def default_locale(self):
		return self._get_value('system', 'default_locale', self.locales[0] if self.locales else None)

	@property
	def memory(self):
		return int(self._get_value('system', 'memory'))

	@property
	def vcpu(self):
		return int(self._get_value('system', 'vcpu'))

	@property
	def has_storage(self):
		return bool(self.storage)

	@property
	def storage(self):
		if not getattr(self, '_storage', None):
			self._storage = []
			storage_layout = self._get_value('storage', 'layout')
			storage_type = self._get_value('storage', 'type')

			if not (storage_layout and storage_type):
				logging.error('Storage layout or storage type not configured')
				return None

			storage_section = "storage_%s" % storage_layout
			if not self.parser.has_section(storage_section):
				logging.error("Storage layout '%s' not configured!" % storage_layout)
				return None

			no_disk = self.parser.getint(storage_section, 'disks')

			global_storage_opts = dict(self.parser.items('storage'))
			for x in ['type', 'layout', 'name']:
				if x in global_storage_opts:
					del global_storage_opts[x]

			for i in range(no_disk):
				self._storage.append((
					get_storage_impl(storage_type,
							name=self.parser.get(storage_section, 'disk%s_name' % i),
							size=Size(self.parser.get(storage_section, 'disk%s_size' % i)),
							filesystem=self.parser.get(storage_section, 'disk%s_fs' % i),
							**global_storage_opts
					),
					self.parser.get(storage_section, 'disk%s_mount' % i)
				))

		return self._storage