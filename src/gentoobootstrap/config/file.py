# -*- coding: utf-8 -*-

from configparser import ConfigParser
from cfgio.keyvalue import KeyValueConfig
from gentoobootstrap.config.base import ConfigBase, NetworkSettings
import logging
import os
from gentoobootstrap.size import Size
from gentoobootstrap.storage import get_impl as get_storage_impl


class FileConfig(ConfigBase):

	def __init__(self, file, **kwargs):
		super(FileConfig, self).__init__(**kwargs)
		file = os.path.abspath(file)
		self.raw_keys = list(kwargs.keys())
		# always pop out the inherit line in the global scope
		self.raw_keys.append('inherit')
		# and the configuration directory for domU configs, too
		self.raw_keys.append('xen_config_dir')

		parser = ConfigParser(defaults=kwargs)
		# this lambda makes the keys in sections case-sensitive
		parser.optionxform = lambda option: option
		parser.read(file)

		# if this file has an 'inherit' setting in DEFAULT, build a list of
		# filenames and re-read the configuration (-> create a new parser)
		inherits = parser.get('DEFAULT', 'inherit', fallback=None)
		if inherits:
			files = [f if os.path.isabs(f) else os.path.join(os.path.dirname(file), f) for f in inherits.split(' ')]
			files.append(file)
			logging.debug("Files to read after expanding 'inherit': %s" % ', '.join(files))
			parser = ConfigParser(defaults=kwargs)
			parser.optionxform = lambda option: option
			parser.read(files)

		self.parser = parser
		self._mirrors = None

	def _make_list(self, value):
		return [x.strip() for x in value.split(',')]

	def _get_value(self, section, option, default=None):
		return self.parser.get(section, option) \
				if self.parser.has_option(section, option) \
				else default

	def _section_to_list(self, section):
		"""
		Turns a single section of the configuration file into an iterable of (key, value).
		If the section does not exist, an empty list is returned.
		"""
		if not self.parser.has_section(section):
			return []

		for k, v in self.parser.items(section):
			if not k in self.raw_keys:
				yield (k, v)

	@property
	def gentoo_mirrors(self):
		if not self._mirrors:
			mirror_string = None

			if self._get_value('bootstrap', 'mirrors', 'inherit') == 'inherit':
				# grab the GENTOO_MIRROS from the host's make.conf
				make_conf = None

				for f in ['/etc/portage/make.conf', '/etc/make.conf']:
					if os.path.exists(f):
						make_conf = KeyValueConfig(f, values_quoted=True)
						break

				if make_conf:
					mirror_string = make_conf.get('GENTOO_MIRRORS').value
				else:
					raise Exception('No GENTOO_MIRRORS variable found in make.conf')

			else:
				mirror_string = self.parser.get('bootstrap', 'mirrors')

			self._mirrors = [x.strip() for x in mirror_string.split(' ')]

		return self._mirrors

	@property
	def portage(self):
		return self._get_value('bootstrap', 'portage', 'fetch')

	@property
	def kernel(self):
		return self._get_value('system', 'kernel')

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
	def timezone(self):
		return self._get_value('system', 'timezone', 'UTC')

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
							domu_device=self.parser.get(storage_section, 'disk%s_device' % i),
							filesystem=self.parser.get(storage_section, 'disk%s_fs' % i),
							opts=self._get_value(storage_section, 'disk%s_opts' % i, None),
							**global_storage_opts
					),
					self.parser.get(storage_section, 'disk%s_mount' % i)
				))

		return self._storage

	@property
	def root_storage(self):
		return next(storage for storage, mount in self.storage if mount == "/")

	@property
	def network(self):
		br = self.parser.get('network', 'bridge')
		auto = self._get_value('network', 'config', 'auto') == 'auto'

		net_config = None

		if not auto:
			net_config = NetworkSettings(self._get_value('network', 'config'),
										 self._get_value('network', 'gateway'),
										 self._make_list(self._get_value('network', 'dns_servers', '')),
										 self._get_value('network', 'resolv_domain'),
										 self._get_value('network', 'resolv_search'))

		return br, net_config

	@property
	def host_bridge(self):
		return self.parser.get('network', 'bridge')

	@property
	def portage_uses(self):
		return self._section_to_list('portage_uses')

	@property
	def portage_keywords(self):
		return self._section_to_list('portage_keywords')

	@property
	def make_conf_settings(self):
		return self._section_to_list('make.conf')

	@property
	def layman_urls(self):
		return self._make_list(self._get_value('layman', 'overlays', ''))

	@property
	def layman_overlays(self):
		return self._make_list(self._get_value('layman', 'add_overlays', ''))

	@property
	def boot_services(self):
		return self._get_value('system', 'boot_services')

	@property
	def merge_list(self):
		return self._get_value('system', 'merge_list')

	@property
	def post_setup_exec(self):
		return self._get_value('post_setup', 'exec')

	@property
	def post_setup_chroot_exec(self):
		return self._get_value('post_setup', 'chroot_exec')