# -*- coding: utf-8 -*-
import logging
import os
import shutil
import traceback
from cfgio.fstab import FstabConfig, FstabEntry
from cfgio.keyvalue import KeyValueConfig, KeyValueConfigValue
from cfgio.simple import SimpleConfig, KeyOnlyValue
from gentoobootstrap.actions.base import ActionBase
from urllib.parse import urljoin
from gentoobootstrap.loader import Loader

from sh import mount, umount, tar, sed, ln, chroot, Command


class GentooLoader(Loader):

	def __init__(self, mirror_urls):
		super(GentooLoader, self).__init__()
		self.mirror_urls = mirror_urls

	def fetch_stage3(self, arch):
		for mirror in self.mirror_urls:
			try:
				latest_file = urljoin(mirror, "releases/{arch}/autobuilds/latest-stage3-{arch}.txt".format(arch=arch))
				latest = self.download(latest_file)

				with open(latest, 'r') as f:
					content = f.read().split('\n')

				content = [x for x in content if x and not x.startswith('#')]

				if content and len(content) == 1:
					url = urljoin(mirror, "releases/{arch}/autobuilds/{url}".format(arch=arch, url=content[0]))
					logging.debug("Downloading url: %s" % url)

					return self.download(url)

			except Exception as ex:
				logging.error("Could not load stage3 from %s: %s" % (mirror, ex))
				logging.error(traceback.format_exc())

		return None


	def fetch_portage(self, outfile):
		for mirror in self.mirror_urls:
			try:
				url = urljoin(mirror, 'snapshots/portage-latest.tar.bz2')
				logging.debug("Downloading url: %s" % url)
				return self.download(url, outfile)
			except Exception as ex:
				logging.error("Downloading portage snapshot from %s failed: %s" % (mirror, ex))

		return False


class InstallGentooAction(ActionBase):

	def __init__(self, config, personalize=True):
		super(InstallGentooAction, self).__init__(config)
		self.do_personalization = personalize
		self.clean_resolv_conf = False

	def test(self):
		return True

	def is_mounted(self, mountpoint):
		mounts = FstabConfig('/proc/mounts')
		return mounts.find(lambda x: x.mountpoint == mountpoint) is not None

	def _prepare(self):
		"""Mounts all configured storage devices"""

		# mount the device to our chroot
		logging.debug("Mounting root %s to %s" % (self.config.root_storage.device, self.config.working_directory))
		mount(self.config.root_storage.device, self.config.working_directory)

		# mount other device(s), if any
		for storage, mountpoint in self.config.storage:
			if mountpoint == "/" or not mountpoint:
				continue

			mountpoint = os.path.join(self.config.working_directory, mountpoint.lstrip('/'))
			logging.debug("Mounting %s to %s" % (storage.device, mountpoint))
			if not os.path.exists(mountpoint):
				os.makedirs(mountpoint)
			mount(storage.device, mountpoint)

	def _cleanup(self):
		"""Unmounts all from the current installation run in the correct order"""

		if self.clean_resolv_conf and os.path.exists(self._path('/etc/resolv.conf')):
			os.remove(self._path('/etc/resolv.conf'))

		if self.is_mounted(self.config.working_directory):
			mounts = FstabConfig('/proc/mounts')
			chroot_mounts = mounts.find_all(lambda x: x.mountpoint.startswith(self.config.working_directory))

			for m in sorted(chroot_mounts, key=lambda x: x.mountpoint, reverse=True):
				logging.debug("Unmounting %s" % m.mountpoint)
				umount(m.mountpoint)

		os.rmdir(self.config.working_directory)

	def _path(self, path):
		"""
		Returns the properly build path name of path in self.config.working_directory
		"""
		return os.path.join(self.config.working_directory, path.lstrip('/'))

	def _print_summary(self):
		logging.info("--------------------------------------------------------------")
		logging.info("Name:            %s" % self.config.name)
		logging.info("root's password: %s" % self.config.root_password)
		logging.info("")
		logging.info("Resources:")
		logging.info("  vCPU:          %s" % self.config.vcpu)
		logging.info("  Memory:        %s" % self.config.memory)
		logging.info("  Harddisks:")
		for storage, mount in self.config.storage:
			logging.info("    {:<12} {}".format(mount or storage.filesystem, storage.size))

		logging.info("  Network (eth0):")
		bridge, net = self.config.network
		logging.info("    Bridge:      %s" % bridge)
		logging.info("    MAC:         %s" % self.config.mac_address)
		if net:
			logging.info("    IP:          %s" % net.config)
			logging.info("    GW:          %s" % net.gateway)
			logging.info("    DNS:         %s" % ', '.join(net.dns_servers))
			logging.info("    Search:      %s" % net.resolv_search)
			logging.info("    Domain:      %s" % net.resolv_domain)
		else:
			logging.info("    DHCP")
		logging.info("--------------------------------------------------------------")

	def execute(self):
		try:
			self._print_summary()
			self._prepare()

			logging.info("Fetching and unpacking archive(s)...")

			# load the latest stage3 archive
			loader = GentooLoader(self.config.gentoo_mirrors)

			stage3 = loader.fetch_stage3(self.config.arch)
			if not stage3:
				raise Exception("Could not load stage3 archive from one of the mirrors: %s" % ', '.join(self.config.gentoo_mirrors))

			# extract stage3 archive to chroot
			tar("xjpf", stage3, "-C", self.config.working_directory)

			if self.config.portage == 'fetch':
				# get the portage snapshot and extract it to usr/portage
				portage = loader.fetch_portage()
				if not portage:
					raise Exception("Could not load portage snapshot")
				tar("xjf", portage, '-C', self._path('/usr/'))
			elif self.config.portage == 'inherit':
				if not os.listdir('/usr/portage'):
					raise Exception("You don't have a portage tree mounted at /usr/portage.")

				wd_portage = self._path('/usr/portage')
				if not os.path.exists(wd_portage):
					os.makedirs(wd_portage)

				# bind-mount the hosts /usr/portage to usr/portage
				logging.debug("Bind'ing /usr/portage to %s" % wd_portage)
				mount('-o', 'bind', '/usr/portage', wd_portage)

			if self.do_personalization:
				self.personalize()

		except Exception as ex:
			logging.error("Installing gentoo failed: %s" % ex)
			logging.error(traceback.format_exc())
		finally:
			self._cleanup()

	def personalize(self):
		logging.info("Personalizing installation...")

		if self.config.locales:
			logging.debug("Configuring locales...")
			locale_gen = SimpleConfig(self._path('/etc/locale.gen'))
			for locale in self.config.locales:
				locale_gen.set(KeyOnlyValue(locale))
			locale_gen.save()


		logging.debug("Writing /etc/fstab")
		fstab = FstabConfig(self._path('/etc/fstab'))
		fstab.remove('/dev/BOOT') # will be added later if someone defined a custom partition for /boot

		for storage, mountpoint in self.config.storage:
			if mountpoint == "/":
				x = fstab.get('/dev/ROOT')
				x.device = storage.domu_device
				x.filesystem = storage.filesystem
				fstab.set(x)
			elif storage.filesystem == "swap":
				x = fstab.get('/dev/SWAP')
				x.device = storage.domu_device
				fstab.set(x)
			else:
				fstab.set(FstabEntry(storage.device, mountpoint, storage.filesystem, 'defaults', 0, 2))

		fstab.save()

		logging.debug("Setting hostname to '%s'" % self.config.fqdn)
		with KeyValueConfig(self._path('/etc/conf.d/hostname'), values_quoted=True) as cfg:
			cfg.set(KeyValueConfigValue('hostname', self.config.hostname))

		with KeyValueConfig(self._path('/etc/hosts'), separator="\t") as cfg:
			cfg.set(KeyValueConfigValue("127.0.0.1", "{fqdn} {hostname} localhost".format(fqdn=self.config.fqdn, hostname=self.config.hostname)))

		logging.debug("Applying portage USEs and keywords...")
		if self.config.portage_uses:
			with KeyValueConfig(self._path('/etc/portage/package.use'), separator=" ") as package_use:
				for pkg, use in self.config.portage_uses:
					package_use.set(KeyValueConfigValue(pkg, use))

		if self.config.portage_keywords:
			with KeyValueConfig(self._path('/etc/portage/package.keywords'), separator=" ") as package_keywords:
				for pkg, kwds in self.config.portage_keywords:
					package_keywords.set(KeyValueConfigValue(pkg, kwds))

		if self.config.make_conf_settings:
			logging.debug("Applying make.conf settings...")
			with KeyValueConfig(self._path('/etc/portage/make.conf'), values_quoted=True) as cfg:
				mirrors = False
				for k, v in self.config.make_conf_settings:
					if k == "GENTOO_MIRRORS":
						mirrors = True
					if k == "DISTDIR" and not os.path.exists(self._path(v)):
						os.makedirs(self._path(v))

					cfg.set(k, v)

				if not mirrors:
					cfg.set('GENTOO_MIRRORS', ' '.join(self.config.gentoo_mirrors))

		logging.debug("Setting up network configuration")
		host_bridge, netsettings = self.config.network
		if netsettings:
			with KeyValueConfig(self._path('/etc/conf.d/net'), values_quoted=True) as cfg:
				cfg.set("config_eth0", netsettings.config)
				cfg.set("routes_eth0", "default via %s" % netsettings.gateway)
				cfg.set('dns_servers_eth0', ' '.join(netsettings.dns_servers))
				if netsettings.resolv_domain:
					cfg.set('dns_domain_eth0', netsettings.resolv_domain)
				if netsettings.resolv_search:
					cfg.set('dns_search_eth0', netsettings.resolv_search)

		self.clean_resolv_conf = not os.path.exists(self._path('/etc/resolv.conf'))
		shutil.copy('/etc/resolv.conf', self._path('/etc/resolv.conf'))

		with open(self._path('/etc/timezone'), 'w') as f:
			f.write(self.config.timezone)

		tz_file = self._path(os.path.join('/usr/share/zoneinfo/', self.config.timezone))
		if os.path.exists(tz_file):
			if os.path.exists(self._path('/etc/localtime')):
				os.remove(self._path('/etc/localtime'))
			ln("-s", os.path.join('/usr/share/zoneinfo/', self.config.timezone), self._path('/etc/localtime'))
		else:
			logging.warning("Zoneinfo file %s does not exist" % tz_file)

		self.personalize_chroot()

	def personalize_chroot(self):
		chroot_helper = None

		for x in [os.path.join(os.path.dirname(__file__), '../../../tools/chroot-bootstrap.sh'),
					'/usr/share/gentoo-bootstrap/chroot-bootstrap.sh']:
			if os.path.exists(x):
				chroot_helper = x
				break

		shutil.copy(chroot_helper, self._path('/root/bootstrap.sh'))

		if self.config.post_setup_chroot_exec:
			logging.debug("Installing post-setup chroot executable: %s" % self.config.post_setup_chroot_exec)
			shutil.copy(self.config.post_setup_chroot_exec, self._path('/root/chroot_exec'))
			os.chmod(self._path('/root/chroot_exec'), 755)
			os.chown(self._path('/root/chroot_exec'), 0, 0)

		mount('-o', 'bind', '/dev', self._path('/dev'))
		mount('-t', 'proc', 'none', self._path('/proc'))

		args = [ '-l', self.config.default_locale,
				 '-p', self.config.root_password,
				 '-e', self.config.merge_list or '',
				 '-u', ' '.join(self.config.layman_urls),
				 '-o', ' '.join(self.config.layman_overlays),
				 '-s', self.config.boot_services or ''
		]

		logging.info("Setting up system in chroot. Depending on your default emerge list this takes some time...")
		cmd = None
		try:
			cmd = chroot(self.config.working_directory, '/bin/bash', '/root/bootstrap.sh', *args, _iter=True)
			for line in cmd:
				logging.debug(line.strip())

			if self.config.post_setup_exec:
				logging.info("Executing post-setup executable: %s" % self.config.post_setup_exec)
				c = Command(self.config.post_setup_exec)
				cmd = c(self.config.working_directory)
				for line in cmd:
					logging.debug(line.strip())

		except Exception as ex:
			# TODO: Make the output nicer and de-duplicate
			logging.fatal("EXCEPTION:")
			logging.fatal(ex)

			if getattr(ex, 'stdout', None):
				logging.fatal("STDOUT: ")
				for line in str(ex.stdout, encoding='utf-8') .split('\n'):
					logging.fatal(line)
			if getattr(ex, 'stderr', None):
				logging.fatal("STDERR: ")
				for line in str(ex.stderr, encoding='utf-8').split('\n'):
					logging.fatal(line)
		finally:
			for p in [self._path('/root/bootstrap.sh'), self._path('/root/chroot_exec')]:
				if os.path.exists(p):
					os.remove(p)

