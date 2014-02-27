# -*- coding: utf-8 -*-

from argparse import ArgumentParser
import random
import sys, os, logging, traceback, tempfile
from urllib.parse import urljoin
from urllib.request import urlopen
import shutil

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from sh import Command, lvcreate, lvremove, mount, umount, wget, ls, tar, sed, chmod, chroot, cp

from gentoobootstrap.cfg.bash import BashReadOnlyConfig
from gentoobootstrap.size import Size


def is_mounted(mountpoint):
	with open('/proc/mounts', 'r') as f:
		for src, dest, fs, opts, dump, pazz in [tuple(x.strip().split(' ')) for x in f.readlines()]:
			if dest == mountpoint:
				logging.debug("%s is mounted on %s (fs: %s, opts=%s)" % (src, dest, fs, opts))
				return True

	return False


def read_mirrors():
	make_conf = None
	for x in ['/etc/make.conf', '/etc/portage/make.conf']:
		try:
			c = BashReadOnlyConfig(x)
			mirrors = c.get('GENTOO_MIRRORS')
			if mirrors:
				return mirrors
		except IOError as ioe:
			logging.warning("File does not exist: %s (%s)" % (x, ioe))


class Fetcher(object):

	def __init__(self, url, cache_dir='/tmp'):
		self.base_url = url
		self.cache_dir = cache_dir

	def fetch_stage3(self, arch, outfile):
		latest_file = urljoin(self.base_url, "releases/{arch}/autobuilds/latest-stage3-{arch}.txt".format(arch=arch))
		logging.debug("Fetching 'latest' file: %s" % latest_file)

		r = urlopen(latest_file, timeout=15)
		content = str(r.read(), encoding='UTF-8').split('\n')
		content = [x for x in content if x and not x.startswith('#')]

		if content and len(content) == 1:
			url = urljoin(self.base_url, "releases/{arch}/autobuilds/{url}".format(arch=arch, url=content[0]))
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

		return False


def create(name, size, volume_group, filesystem, arch, fqdn, kernel_image):
	root = tempfile.mkdtemp()

	try:
		lv_name = "%s-hdd0" % name
		lv_device = "/dev/%s/%s" % (volume_group, lv_name)

		domU_config = os.path.join('/etc/xen/', "%s.cfg" % name)

		if os.path.exists(lv_device) or os.path.exists(domU_config):
			raise Exception("%s or %s already exist!" % (lv_device, domU_config))

		# create lvm volume
		logging.info("Creating LVM volume '%s'" % lv_name)
		lvcreate("-L", size, "-n", lv_name, volume_group)

		if not os.path.exists(lv_device):
			raise Exception("Could not find created lvm volume (looked for %s)" % lv_device)

		# format root fs
		logging.info("Creating '%s' filesystem on %s" % (filesystem, lv_device))
		Command("mkfs.%s" % filesystem)(lv_device)

		# mount the volume to a temporary directory
		mount(lv_device, root)

		# fetch stage3 tarball and unpack it to the root fs
		logging.info("Fetching stage tarball")

		mirrors = read_mirrors()
		if not mirrors:
			raise Exception("Could not read gentoo mirrors to fetch stage3")
		mirrors = [x.strip() for x in mirrors.split(' ')]

		stage3 = os.path.join(root, 'stage3.tar.bz2')
		for mirror in mirrors:
			if Fetcher(mirror).fetch_stage3(arch, stage3):
				break

		if not os.path.exists(stage3):
			raise Exception("Could not download stage3 archive")

		logging.info("Extracting stage3...")
		tar("xjpf", stage3, "-C", root)
		os.remove(stage3)

		if not os.listdir('/usr/portage'):
			raise Exception("You don't have a portage tree mounted at /usr/portage. Cannot proceed (for now)")

		logging.debug("Preparing chroot")
		chroot_portage = os.path.join(root, 'usr/portage/')
		if not os.path.exists(chroot_portage):
			os.makedirs(chroot_portage)

		mount('-o', 'bind', '/dev/', os.path.join(root, 'dev/'))
		mount('-t', 'proc', 'none', os.path.join(root, 'proc/'))
		mount('-o', 'bind', '/usr/portage', chroot_portage)


		logging.info("Patching files in %s" % root)

		logging.debug("Patching: /etc/locale.gen")
		locales = ['en_GB.UTF-8 UTF-8', 'en_US.UTF-8 UTF-8', 'de_DE.UTF-8 UTF-8']
		with open(os.path.join(root, 'etc/locale.gen'), 'a') as o:
			o.write('\n'.join(locales))

		logging.debug("Setting FQDN to %s" % fqdn)
		hostname = fqdn[:fqdn.index('.')]
		sed('-e', 's/127\.0\.0\.1.*/127.0.0.1\t{fqdn} {hostname} localhost/g'.format(fqdn=fqdn, hostname=hostname), os.path.join(root, 'etc/hosts'))
		sed('-e', 's/hostname=.*/hostname="%s"/g' % hostname, os.path.join(root, 'etc/conf.d/hostname'))

		logging.debug("Setting USEs in /etc/portage/package.use")
		with open(os.path.join(root, 'etc/portage/package.use'), 'a+') as o:
			o.write('dev-vcs/git -gpg -perl -python\n')
			o.write('app-portage/layman git -cvs -subversion\n')

		logging.debug("Setting DNS stuff in /etc/resolv.conf")
		cp('/etc/resolv.conf', os.path.join(root, 'etc/resolv.conf'))

		logging.info('Writing setup script in /root/bootstrap.sh')
		with open(os.path.join(root, 'root/bootstrap.sh'), 'w') as o:
			bootstrap_jobs = 5
			code = """
#!/bin/bash
source /usr/lib64/portage/bin/isolated-functions.sh
locale-gen
eselect locale set en_US.utf8
sed -i '/c1:.*/ih0:12345:respawn:\/sbin\/agetty --noclear 9600 hvc0 screen' /etc/inittab || die "failed to enable serial console"
sed -i '/c[0-9]:.*/ s/^/#/' /etc/inittab || die "Failed to remove default tty"
#grep -A 15 TERMINALS /etc/inittab

env-update && source /etc/profile
einfo "Running emerge --regen"
emerge --regen > /dev/null || die "portage regen failed"
#emerge layman -v --jobs={njobs} || die "Could not emerge layman"
#layman -S && layman -a last-hope && echo "source /var/lib/layman/make.conf" >> /etc/portage/make.conf || die "Adding overlay last-hope failed"

ln -s /etc/init.d/net.lo /etc/init.d/net.eth0
rc-update add net.eth0 default
rc-update add sshd default

echo "foo\nfoo" | passwd root
"""
			foo="""
password=$(< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c${1:-16};echo;)
echo "${{password}}\n${{password}}" | passwd root
einfo "You root password: ${{password}} (CHANGE IT!)"
"""
			o.write(code.format(njobs=bootstrap_jobs))
			chmod('u+x', os.path.join(root, 'root/bootstrap.sh'))

		logging.info("Executing bootstrap.sh in chroot")
		for x in chroot(root, '/bin/bash', '/root/bootstrap.sh', _iter=True):
			logging.info(">> %s" % x.rstrip('\n'))


		bridge="br0"
		mac = ':'.join(map(lambda x: "%02x" % x, [0x00, 0x16, 0x3e,
								random.randint(0x00, 0x7f),
								random.randint(0x00, 0xff),
								random.randint(0x00, 0xff)]))

		logging.info("Writing domU config...")
		cfg="""kernel = "{kernel_image}"
vcpus  = 4
memory = 1024
name   = "{name}"
disk   = [ 'phy:{root_dev},xvda1,w' ]
root   = "/dev/xvda1"
vif    = [ 'mac={mac},bridge=br0', ]
"""
		with open(domU_config, 'w') as o:
			o.write(cfg.format(kernel_image=kernel_image, name=name, mac=mac, root_dev=lv_device))

	finally:
		if root:
			for x in ['dev', 'proc', 'usr/portage']:
				p = os.path.join(root, x)
				if is_mounted(p):
					umount(p)

			if is_mounted(root):
				umount(root)

			os.rmdir(root)

def main():
	parser = ArgumentParser()
	parser.add_argument('-n', '--name', required=True, help="The name of the domU")
	parser.add_argument('-s', '--root-size', required=True, help="The size of the root filesystem")
	parser.add_argument('-vg', '--volume-group', required=True, help="The name of the LVM volume group to create the devices in")
	parser.add_argument('-fs', '--filesystem', default="ext4", help="The filesystem to create on the volume. Should map to an mkfs wrapper")
	parser.add_argument('-v', '--verbose', action="count", default=3)
	parser.add_argument('--arch', default='amd64', choices=['amd64', 'x86'])
	parser.add_argument('--fqdn', required=True, help="The new domU's FQDN")
	parser.add_argument('-k', '--kernel', default="/boot/vm-kernel")

	args = parser.parse_args()

	logging.basicConfig(level=logging.FATAL - (10 * args.verbose), format='%(asctime)s %(levelname)-7s %(message)s')

	try:
		create(args.name, Size(args.root_size), args.volume_group, args.filesystem, args.arch, args.fqdn, args.kernel)

		return 0
	except Exception as ex:
		logging.fatal("Failed to create domU: %s" % ex)
		logging.fatal(traceback.format_exc())
		return 1

if __name__ == "__main__":
	sys.exit(main())