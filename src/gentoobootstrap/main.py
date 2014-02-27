#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import tempfile
import logging
from argparse import ArgumentParser
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from gentoobootstrap.actions.domuconfig import CreateDomUConfig
from gentoobootstrap.actions.storage import CreateStorageAction
from gentoobootstrap.config.file import FileConfig


class Bootstrap(object):

	def __init__(self, config):
		self.config = config

	def check(self, actions):
		logging.debug("Executing pre-flight checks...")

		for action in actions:
			if not action.check():
				logging.error("Action '%s' failed to pass pre-execution tests" % action.__class__.__name__)
				return False

		return True

	def execute(self):
		base_dir = tempfile.mkdtemp()
		logging.debug("Base directory: %s" % base_dir)

		try:
			actions = [
				CreateStorageAction(self.config),
				CreateDomUConfig(self.config)
			]

			if not self.check(actions):
				return

			logging.info("Pre-execution tests passed. Starting bootstrapping")

			for action in actions:
				action.execute()

			#  1) Create storage
			#  2) format storage
			#  3) Extract stageX
			#  4) Patch configs: locale.gen, make.conf, portage.keywords/.use, fstab
			#  5)
			#  9) write chroot setup.sh/.py
			# 10) mount dev, proc, sys(?) and exec setup script in chroot
			# 11) set root pwd

			pass
		except Exception as e:
			logging.error(e)
			logging.error(traceback.format_exc())
		finally:
			if os.path.exists(base_dir):
				os.rmdir(base_dir)


def main():
	parser = ArgumentParser()

	parser.add_argument('-c', '--config', required=True)
	parser.add_argument('-n', '--name', required=True, help="The name of the domU")
	parser.add_argument('-f', '--fqdn', required=True, help="The full-qualified domain name")
	parser.add_argument('-v', '--verbose', action="count", default=3)
	parser.add_argument('--no-color', action='store_true', help='Do not colorize log output')

	args = parser.parse_args()

	logging.basicConfig(level=logging.FATAL - (10 * args.verbose),
						format='%(asctime)s %(levelname)-7s %(message)s')

	if not args.no_color:
		import gentoobootstrap.log

	cfg = FileConfig(args.config, name=args.name, fqdn=args.fqdn)
	Bootstrap(cfg).execute()

	#print("Arch: %s" % cfg.arch)
	#print("Locales: %s (default: %s)" % (cfg.locales, cfg.default_locale))
	#print("Memory: %s" % cfg.memory)
	#print("CPU: %s" % cfg.vcpu)

	#print("Storage:")
	#for storage, mount in cfg.storage:
	#	print(" %s on %s" % (storage, mount, ))



if __name__ == "__main__":
	main()