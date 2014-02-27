# -*- coding: utf-8 -*-
from gentoobootstrap.storage.lvm import LVMStorage


def get_impl(type, **kwargs):
	if type == "lvm":
		return LVMStorage(**kwargs)
	else:
		raise Exception("Unsupported storage type '%s'" % type)