# -*- coding: utf-8 -*-


class ActionBase(object):

	def __init__(self, config):
		self.config = config

	def test(self):
		return False

	def execute(self):
		pass