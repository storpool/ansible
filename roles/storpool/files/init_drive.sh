#!/bin/bash -xe

if [ -z "$2" ]; then
	echo Usage: $0 device node-with-initial-drive
	exit 2
fi

dev="$1"
initdrivenode="$2"

if ! [ -b "$dev" ]; then
	echo $dev is not a block device
	# currently impossible to differentiate between missing drive and
	# already intialized one with storpool_nvmed running
	exit 1 
fi

if ! [ -f /etc/storpool.conf ]; then
	echo storpool.conf not installed
	exit 1
fi

id=`storpool_showconf -n SP_OURID`

if [ -z "$id" ]; then
	echo SP_OURID not defined
	exit 1
fi

if storpool_initdisk --list |grep -q ^$dev; then
	# already initialized
	exit 0
fi

last=`storpool_initdisk --list |awk '/diskId/ {print $3 }'|tr -d ,|sort -n |tail -n1`

if [ -z "$last" ]; then
	num=${id}11
else
	let num=$last+1 || true
fi

if [ "${dev#/dev/nvme}" != "$dev" ] ; then
    part=${dev}p1
else
    part=${dev}1
fi

if ! [ -b ${part} ] ; then
	echo partitions do not exist, creating
	parted -s --align optimal ${dev} mklabel gpt -- mkpart primary 2MiB 100%
	sleep 1
fi

if [ "$initdrivenode" == "${HOSTNAME}" ] && ! [ -f /etc/storpool/initialdrive.ansible ]; then
	touch /etc/storpool/initialdrive.ansible
	init=-I
else
	init=
fi

storpool_initdisk $init $num $part || true
