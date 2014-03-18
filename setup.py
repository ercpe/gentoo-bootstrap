#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(name='gentoo-bootstrap',
		version='0.1',
		description='Tool to ease the creation of gentoo-based XEN DomUs',
		author='Johann Schmitz',
		author_email='johann@j-schmitz.net',
		url='https://github.com/ercpe/gentoo-bootstrap',
		packages=['gentoobootstrap', 'gentoobootstrap.actions', 'gentoobootstrap.config', 'gentoobootstrap.storage'],
		package_dir={'': 'src'},
)