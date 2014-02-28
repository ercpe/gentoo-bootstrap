# -*- coding: utf-8 -*-
import logging
import os
import shutil
import traceback
from cfgio.fstab import FstabConfig
from gentoobootstrap.actions.base import ActionBase
from urllib.parse import urljoin
from urllib.request import urlopen

from sh import mount, umount

class GentooStageLoader(object):

	def __init__(self, mirror_urls, cache_dir='/tmp'):
		self.mirror_urls = mirror_urls
		self.cache_dir = cache_dir

	def fetch_stage3(self, arch, outfile):
		for mirror in self.mirror_urls:
			try:
				latest_file = urljoin(mirror, "releases/{arch}/autobuilds/latest-stage3-{arch}.txt".format(arch=arch))
				logging.debug("Fetching 'latest' file: %s" % latest_file)

				r = urlopen(latest_file, timeout=15)
				content = str(r.read(), encoding='UTF-8').split('\n')
				content = [x for x in content if x and not x.startswith('#')]

				if content and len(content) == 1:
					url = urljoin(mirror, "releases/{arch}/autobuilds/{url}".format(arch=arch, url=content[0]))
					logging.info("Fetching stage3 tarball from %s..." % url)

					cache_file = os.path.join(self.cache_dir, os.path.basename(content[0]))
					if os.path.exists(cache_file):
						logging.info("Using cached file %s" % cache_file)
						shutil.copy(cache_file, outfile)
						return True
					else:
						logging.info("Downloading %s to cache (%s)" % (url, cache_file))

						with open(cache_file, 'wb') as o:
							r = urlopen(url, timeout=15)

							x = r.read(1024)
							while x:
								o.write(x)
								x = r.read(1024)

					if os.path.exists(cache_file):
						logging.info("Using cached file %s" % cache_file)
						shutil.copy(cache_file, outfile)

					return True

			except Exception as ex:
				logging.error("Could not load stage3 from %s: %s" % (mirror, ex))
				logging.error(traceback.format_exc())

		return False

class InstallGentooAction(ActionBase):

	def check(self):
		return True

	def is_mounted(self, mountpoint):
		mounts = FstabConfig('/proc/mounts')
		return mounts.find(lambda x: x.mountpoint == mountpoint) is not None

	def execute(self):

		try:
			mount(self.config.root_storage.device, self.config.working_directory)

			loader = GentooStageLoader(self.config.gentoo_mirrors)

			stage3 = os.path.join(self.config.working_directory, 'stage3.tar.bz2')
			if not loader.fetch_stage3(self.config.arch, stage3):
				raise Exception("Could not load stage3 archive from one of the mirrors: %s" % ', '.join(self.config.gentoo_mirrors))

		except Exception as ex:
			logging.error("Installing gentoo failed: %s" % ex)
			logging.error(traceback.format_exc())
		finally:
			if self.is_mounted(self.config.working_directory):
				umount(self.config.working_directory)

			os.rmdir(self.config.working_directory)