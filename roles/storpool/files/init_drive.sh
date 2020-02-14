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

if [[ $(cat /sys/block/${dev#'/dev/'}/queue/rotational) -eq 0 ]]; then
    ssd='-s'
else
    ssd=
fi

if [ -z "$ssd" ]; then
    last=`storpool_initdisk --list | grep -v SSD | awk '/diskId/ {print $3}' | tr -d , | sort -n | tail -n1`
else
    last=`storpool_initdisk --list | grep SSD | awk '/diskId/ {print $3}' | tr -d , | sort -n | tail -n1`
fi

if [ -z "$last" ]; then
    if [ -z "$ssd" ]; then
	num=${id}11
    else
	num=${id}01
    fi
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

if [ "$initdrivenode" == "$(hostname -f)" ] && ! [ -f /etc/storpool/initialdrive.ansible ]; then
	touch /etc/storpool/initialdrive.ansible
	init=-I
else
	init=
fi

storpool_initdisk $init $ssd $num $part || true
