# -*- coding: utf-8 -*-
import logging
import os
import random
import shutil
import string
import traceback
from cfgio.fstab import FstabConfig, FstabEntry
from cfgio.keyvalue import KeyValueConfig, KeyValueConfigValue
from cfgio.simple import SimpleConfig, KeyOnlyValue
from gentoobootstrap.actions.base import ActionBase
from urllib.parse import urljoin
from urllib.request import urlopen

from sh import mount, umount, tar, sed, ln


class GentooStageLoader(object):

	def __init__(self, mirror_urls, cache_dir='/tmp'):
		self.mirror_urls = mirror_urls
		self.cache_dir = cache_dir

	def fetch_stage3(self, arch, outfile):
		for mirror in self.mirror_urls:
			try:
				latest_file = urljoin(mirror, "releases/{arch}/autobuilds/latest-stage3-{arch}.txt".format(arch=arch))

				content = self.download(latest_file).split('\n')
				content = [x for x in content if x and not x.startswith('#')]

				if content and len(content) == 1:
					url = urljoin(mirror, "releases/{arch}/autobuilds/{url}".format(arch=arch, url=content[0]))
					logging.info("Stage3 tarball url: %s" % url)

					if self.download(url, outfile):
						return True

			except Exception as ex:
				logging.error("Could not load stage3 from %s: %s" % (mirror, ex))
				logging.error(traceback.format_exc())

		return False

	def fetch_portage(self, outfile):
		for mirror in self.mirror_urls:
			try:
				url = urljoin(mirror, 'snapshots/portage-latest.tar.bz2')
				if self.download(url, outfile):
					return True
			except Exception as ex:
				logging.error("Downloading portage snapshot from %s failed: %s" % (mirror, ex))

		return False

	def download(self, url, outfile=None):
		if outfile:
			cache_file = os.path.join(self.cache_dir, os.path.basename(outfile))

			if not os.path.exists(cache_file):
				logging.info("Loading %s to %s" % (url, cache_file))
				logging.debug("download(): cache file: %s" % cache_file)

				r = urlopen(url, timeout=15)
				with open(cache_file, 'wb') as o:
					x = r.read(1024)
					while x:
						o.write(x)
						x = r.read(1024)

			logging.debug("Copying cache file %s to %s" % (cache_file, outfile))
			shutil.copy(cache_file, outfile)

			return True
		else:
			logging.info("Loading %s" % url)
			r = urlopen(url, timeout=15)
			return str(r.read(), encoding='UTF-8')


class InstallGentooAction(ActionBase):

	def __init__(self, config, personalize=True):
		super(InstallGentooAction, self).__init__(config)
		self.do_personalization = personalize

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

	def execute(self):
		try:
			self._prepare()

			# load the latest stage3 archive
			loader = GentooStageLoader(self.config.gentoo_mirrors)

			stage3 = self._path('stage3.tar.bz2')
			if not loader.fetch_stage3(self.config.arch, stage3):
				raise Exception("Could not load stage3 archive from one of the mirrors: %s" % ', '.join(self.config.gentoo_mirrors))

			# extract stage3 archive to chroot
			tar("xjpf", stage3, "-C", self.config.working_directory)
			os.remove(stage3)

			if self.config.portage == 'fetch':
				# get the portage snapshot and extract it to usr/portage
				portage = self._path('portage.tar.bz2')
				if not loader.fetch_portage(portage):
					raise Exception("Could not load portage snapshot")
				tar("xjf", portage, '-C', self._path('/usr/'))
				os.remove(portage)
			elif self.config.portage == 'inherit':
				if not os.listdir('/usr/portage'):
					raise Exception("You don't have a portage tree mounted at /usr/portage.")

				wd_portage = self._path('/usr//portage')
				if not os.path.exists(wd_portage):
					os.makedirs(wd_portage)

				# bind-mount the hosts /usr/portage to usr/portage
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
				for k, v in self.config.make_conf_settings:
					cfg.set(k, v)

		logging.debug("Setting up network configuration")
		host_bridge, netsettings = self.config.network
		if netsettings:
			with KeyValueConfig(self._path('/etc/conf.d/net', values_quoted=True)) as cfg:
				cfg.set("config_eth0", netsettings.config)
				cfg.set("routes_eth0", "default via %s" % netsettings.gateway)
			with SimpleConfig(self._path('/etc/resolv.conf')) as cfg:
				for server in netsettings.dns_servers:
					cfg.set("nameserver %s" % server)

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
		def randompassword():
			chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
			return ''.join(random.choice(chars) for _ in range(20))

		pwd = randompassword()
		logging.info("Root password: %s" % pwd)

		code = """#!/bin/bash

function eerr() {
	echo $* >&2
}

function die() {
	eerr $*
	exit 1
}

locale=""
password=""

while getopts "l:p": name; do
	case $name in
		l) locale=$OPTARG;;
		p) password=$OPTARG;;
	esac
done

locale-gen
[[ ! -z "${locale}" ]] && eselect locale set ${locale}
#sed -i '/c1:.*/ih0:12345:respawn:\/sbin\/agetty --noclear 9600 hvc0 screen' /etc/inittab || die "failed to enable serial console"
#sed -i '/c[0-9]:.*/ s/^/#/' /etc/inittab || die "Failed to remove default tty"
##grep -A 15 TERMINALS /etc/inittab

env-update && source /etc/profile
einfo "Running emerge --regen"
emerge --regen > /dev/null || die "portage regen failed"
#emerge layman -v --jobs={njobs} || die "Could not emerge layman"
#layman -S && layman -a last-hope && echo "source /var/lib/layman/make.conf" >> /etc/portage/make.conf || die "Adding overlay last-hope failed"

ln -s /etc/init.d/net.lo /etc/init.d/net.eth0
rc-update add net.eth0 default
rc-update add sshd default

echo "${password}\n${password}" | passwd root
"""