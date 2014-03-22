#!/bin/bash

function eerr() {
	echo $* >&2
}

function die() {
	eerr $*
	exit 1
}

locale=""
password=""
mergelist=""
overlays=""
overlay_urls=""
services=""

while getopts "l:p:e:u:o:s": name; do
	case $name in
		l) locale=$OPTARG;;
		p) password=$OPTARG;;
		e) mergelist=$OPTARG;;
		u) overlay_urls=$OPTARG;;
		o) overlays=$OPTARG;;
		s) services=$OPTARG;;
	esac
done

locale-gen
[[ ! -z "${locale}" ]] && eselect locale set ${locale}
sed -i '/c1:.*/ih0:12345:respawn:\/sbin\/agetty --noclear 38400 hvc0 screen' /etc/inittab || die "failed to enable serial console"
sed -i '/c[0-9]:.*/ s/^/#/' /etc/inittab || die "Failed to remove default tty"
##grep -A 15 TERMINALS /etc/inittab

env-update && source /etc/profile
emerge --regen > /dev/null || die "portage regen failed"
eselect news read &> /dev/null

if [[ ! -z "${overlays}" || ! -z "${overlay_urls}" ]]; then
	emerge layman -v || die "Could not emerge layman"
fi

if [[ ! -z "${overlay_urls}" ]]; then
	for url in ${overlay_urls}; do
		# hack alert!
		sed -i -r "s#^(overlays.*)#\1\n\t${url}#g" /etc/layman/layman.cfg || die "Could not add overlay url ${url}"
	done
fi

if [[ ! -z "${overlays}" ]]; then
	layman -S || die "Could not sync overlays"

	for overlay in ${overlays}; do
		layman -a ${overlay} || die "Could not add overlay ${overlay}"
	done

	echo "source /var/lib/layman/make.conf" >> /etc/portage/make.conf || die "Adding layman to make.conf failed"
fi

if [[ ! -z "${mergelist}" ]]; then
	NOCOLOR="true" emerge --nospinner --color n ${mergelist} || die "Emerging ${mergelist} failed"
fi

ln -s /etc/init.d/net.lo /etc/init.d/net.eth0 || die "Could not symlink net.eth0 to net.lo"
rc-update add net.eth0 default || die "Could not add net.eth0 to default runlevel"
rc-update add sshd default || die "Could not add sshd to default runlevel"

if [[ ! -z "${services}" ]]; then
	for s in ${services}; do
		echo "rc-updating for ${s}"
		rc-update add ${s} default || die "Could not add ${s} to default runlevel"
	done
fi

echo "root:${password}" | chpasswd