#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import tempfile
import logging
from argparse import ArgumentParser
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../cfgio/src'))

from gentoobootstrap.actions.cfgchk import CheckConfigAction
from gentoobootstrap.actions.gentoo import InstallGentooAction
from gentoobootstrap.actions.domuconfig import CreateDomUConfig
from gentoobootstrap.actions.storage import CreateStorageAction
from gentoobootstrap.config.file import FileConfig

class Bootstrap(object):

	def __init__(self, config):
		self.config = config

	def check(self, actions):
		logging.debug("Executing pre-flight checks...")

		for action in actions:
			if not action.test():
				logging.error("Action '%s' failed to pass pre-execution tests" % action.__class__.__name__)
				return False

		return True

	def execute(self, install=True, personalize=True):
		base_dir = tempfile.mkdtemp()
		logging.debug("Base directory: %s" % base_dir)

		try:
			actions = [CheckConfigAction(self.config), CreateStorageAction(self.config)]

			if install:
				actions.append(InstallGentooAction(self.config, personalize=personalize))
			else:
				logging.info("Skipping installation of Gentoo")

			actions.append(CreateDomUConfig(self.config))

			if not self.check(actions):
				return

			logging.info("Pre-execution tests passed. Starting bootstrapping")
			logging.info("Actions: %s" % (', '.join([x.__class__.__name__ for x in actions])))

			for action in actions:
				action.execute()

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
	parser.add_argument('-d', '--xen-config-dir', default='/etc/xen', help="Place the xen domU configuration in DIR (default: %(default)s)")
	parser.add_argument('-v', '--verbose', action="count", default=3)
	parser.add_argument('--no-install', action='store_true', help="Only create the volume and config. Do not install Gentoo.")
	parser.add_argument('--no-personalize', action="store_true", help="Only install Gentoo, but skip personalization")
	parser.add_argument('--no-color', action='store_true', help='Do not colorize log output')

	args = parser.parse_args()

	logging.basicConfig(level=logging.FATAL - (10 * args.verbose),
						format='%(asctime)s %(levelname)-7s %(message)s')

	if not args.no_color:
		import gentoobootstrap.log

	cfg = FileConfig(args.config, name=args.name, fqdn=args.fqdn, xen_config_dir=args.xen_config_dir)
	Bootstrap(cfg).execute(install=not args.no_install, personalize=not args.no_personalize)


if __name__ == "__main__":
	main()