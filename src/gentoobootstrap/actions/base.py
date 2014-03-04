# -*- coding: utf-8 -*-


class ActionBase(object):
	"""
	Base class for all actions. Sub-classes must implement the .test() method and optionally the execute method.
	"""

	def __init__(self, config):
		self.config = config

	def test(self):
		"""This method is called before any action starts execution. Subclasses must implement this method to do
		pre-execution tests. If this method returns False, the bootstrap process will stop.

		Sub-class must not do any modifying actions in this method.
		"""
		return False

	def execute(self):
		"""Action sub-classes must implement this method to do the real work."""
		pass