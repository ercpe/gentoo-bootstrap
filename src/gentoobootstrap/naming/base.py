# -*- coding: utf-8 -*-


class BaseNameCreator(object):

	def __init__(self):
		self.vars = {}

	def setup(self, **kwargs):
		self.vars.update(kwargs)

	def format(self, template):
		return template.format(**self.vars)