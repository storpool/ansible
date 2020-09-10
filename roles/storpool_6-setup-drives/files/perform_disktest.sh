#!/bin/bash -xe

if [ -z "$1" ]; then
	echo Usage: $0 drive drive ...
	exit 2
fi

dirname=/root/storpool/disktest.`date +%s`

if [ -d "$dirname" ]; then
	echo testdir already exists
	exit 2
fi

mkdir -p /etc/storpool

mkdir -p "$dirname"
cd "$dirname"

for i in $*; do
	tries=0
	# we need to wait a bit if the drive is being exposed at the moment
	while ! [ -b "$i" ] && [ $tries -lt 10 ]; do
		sleep 1
		let tries=$tries+1 || true
	done

	if [ $tries -gt 9 ]; then
		echo $i not found
		exit 3
	fi

	if storpool_initdisk --list | grep -q ^$i; then
	# storpool drive - not touching
		continue
	fi

	serial=`/usr/lib/storpool/diskid-helper "$i" 2>/dev/null | grep ^SERIAL|cut -d = -f 2|tr -d ' '`
	if [ -z "$serial" ]; then
		if smartctl -i "$i" | grep -q "Product.*QEMU"; then
			serial=`echo "$i"|sed s%/%_%g`
		else
			echo Cannot detect serial number and not a virtual drive
			exit 4
		fi
	fi
	if [ -f "/etc/storpool/${serial}.tested" ]; then
		continue
	fi
	echo `basename "$i"` >> drives.txt
	echo "$serial" >> serials.txt
done

if [ -f drives.txt ]; then
	for d in `cat drives.txt`; do
		parted -s /dev/${d} mklabel msdos
	done
	/usr/sbin/disk_tester
	for i in `cat serials.txt`; do
		touch "/etc/storpool/${i}.tested"
	done
fi
