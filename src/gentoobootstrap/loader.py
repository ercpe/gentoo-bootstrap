# -*- coding: utf-8 -*-
import logging
import os
from urllib.error import HTTPError
from urllib.request import Request, build_opener
import json


class Loader(object):

	def __init__(self, cache_dir="/tmp"):
		self.cache_dir = cache_dir

	def load_meta(self, f):
		try:
			with open(f, 'r') as i:
				return json.load(i)
		except:
			return {
				'last-modified': None,
				'etag': None
			}

	def save_meta(self, meta, f):
		with open(f, 'w') as o:
			json.dump(meta, o)

	def download(self, url):
		cache_file = os.path.join(self.cache_dir, os.path.basename(url))
		meta_file = "%s.meta" % cache_file
		logging.debug("Cache file: %s" % cache_file)

		if os.path.exists(meta_file) and not os.path.exists(cache_file):
			os.remove(meta_file)

		meta = self.load_meta(meta_file)

		request = Request(url)
		if meta.get('last-modified', None):
			logging.debug("Last-Modified: %s" % meta['last-modified'])
			request.add_header('If-Modified-Since', meta['last-modified'])

		if meta.get('etag', None):
			logging.debug("Etag: %s" % meta['etag'])
			request.add_header('If-None-Match', meta['etag'])


		request.add_header('Accept', 'application/octect-stream')
		request.add_header('User-Agent', 'gentoo-bootstrap/0.1')

		try:
			opener = build_opener()
			response = opener.open(request)

			last_modified = None

			if 'Last-Modified' in response.headers:
				meta['last-modified'] = response.headers['Last-Modified']
			if 'Etag' in response.headers:
				meta['etag'] = response.headers['etag']

			bytes_read = 0
			with open(cache_file, 'wb') as o:
				x = response.read(1024)
				bytes_read += len(x)
				while x:
					o.write(x)
					x = response.read(1024)
					bytes_read += len(x)

			logging.debug("Downloaded %s bytes to %s" % (bytes_read, cache_file))
		except HTTPError as he:
			logging.debug("Not modified. Cache file is valid")
			if not he.getcode() == 304:
				raise he

		self.save_meta(meta, meta_file)

		return cache_file

