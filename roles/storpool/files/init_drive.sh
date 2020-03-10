#!/bin/bash -xe

if [ -z "$2" ]; then
	echo Usage: $0 device node-with-initial-drive
	exit 2
fi

MAXGB=4000

dev="$1"
initdrivenode="$2"
maxpartsize=$((${MAXGB}*10**9))

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

parted -s ${dev} mklabel gpt

if [ "${dev#/dev/nvme}" != "${dev}" ]; then
# nvme init
	dsize=$(lsblk -ndbo SIZE ${dev})

	if [ ${dsize} -gt ${maxpartsize} ]; then
		parts=$((${dsize}/${maxpartsize}+1))
	else
		parts=1
	fi

	p=1
	while [ ${p} -le ${parts} ]; do
		if [ ${p} -eq 1 ]; then
			pstart="2MiB"
			last=$(storpool_initdisk --list | grep SSD | awk '{print $3}' | tr -d , | sort -n | tail -n1)
			if [ -z "$last" ]; then
				num=${id}01
			else
				let num=${last}+1 || true
			fi
		else
			pstart="$((100/${parts}*(${p}-1)))%"
			let num=${num}+1 || true
		fi
		if [ ${p} -eq ${parts} ]; then
			pend="100%"
		else
			pend="$((100/${parts}*${p}))%"
		fi

		parted -s --align optimal ${dev} mkpart storpool ${pstart} ${pend}

		if [ "${initdrivenode}" = "$(hostname -f)" ] && ! [ -f /etc/storpool/initialdrive.ansible ]; then
			touch /etc/storpool/initialdrive.ansible
			init='-I'
		else
			init=
		fi

		udevadm settle
		storpool_initdisk ${init} -s ${num} ${dev}p${p} || true

		let p=${p}+1 || true
	done
else
# drive init
	if [ $(cat /sys/block/${dev#'/dev/'}/queue/rotational) -eq 0 ]; then
		ssd='-s'
	else
		ssd=
	fi
	if [ -z "$ssd" ]; then
		last=$(storpool_initdisk --list | grep -v SSD | awk '/diskId/ {print $3}' | tr -d , | sort -n | tail -n1)
	else
		last=$(storpool_initdisk --list | grep SSD | awk '/diskId/ {print $3}' | tr -d , | sort -n | tail -n1)
	fi
	if [ -z "$last" ]; then
		if [ -z "$ssd" ]; then
			num=${id}11
		else
			num=${id}01
		fi
	else
		let num=${last}+1 || true
	fi
	parted -s --align optimal ${dev} mkpart storpool 2MiB 100%

	if [ "${initdrivenode}" = "$(hostname -f)" ] && ! [ -f /etc/storpool/initialdrive.ansible ]; then
		touch /etc/storpool/initialdrive.ansible
		init='-I'
	else
		init=
	fi

	udevadm settle
	storpool_initdisk ${init} ${ssd} ${num} ${dev}1 || true
fi
