# -*- coding: utf-8 -*-
from gentoobootstrap.storage.filesystem import FilesystemStorage


def get_impl(type, **kwargs):
	return get_impl_class(type)(**kwargs)


def get_impl_class(type):
	if type == "lvm":
		from gentoobootstrap.storage.lvm import LVMStorage
		return LVMStorage
	elif type == 'filesystem':
		return FilesystemStorage
	else:
		raise Exception("Unsupported storage type '%s'" % type)