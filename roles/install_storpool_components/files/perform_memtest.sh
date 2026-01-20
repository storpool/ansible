#!/bin/bash -e

epoch_start=$(date --utc +%s)
ipmitool="/usr/bin/ipmitool"
memchips=$(dmidecode -t memory|grep "Serial Number:"|cut -d: -f 2|md5sum|awk '{print $1}')

if [[ -f "/etc/storpool/${memchips}.memtested" ]]; then
	exit 0
fi

ARCH=$(uname -m)

if [[ "${ARCH}" = "aarch64" ]]; then
    binary="memtester-aarch64"
else
    binary="memtester"
fi

if [[ $(pgrep -xc kvm) -gt 0 ]] || [[ $(pgrep -xc qemu) -gt 0 ]]; then
	echo "Found running qemu processes. Bailing out."
	exit 1
fi

if [[ -e "${1}/${binary}" ]]; then
	MT="${1}/${binary}"
elif [[ -e "/usr/local/bin/${binary}" ]]; then
	MT="/usr/local/bin/${binary}"
elif [[ -e "/root/storpool/${binary}" ]]; then
	MT="/root/storpool/${binary}"
else
	echo "Error: ${binary} not found"
	exit 1
fi

if ! [[ -d /etc/storpool ]]; then
	mkdir /etc/storpool
fi


swapoff -a
sync
sysctl vm.drop_caches=3

for i in /sys/devices/system/node/node*; do
	node=${i##*/}
	nodenum=${node//node/}
	memavail=$(grep "MemFree:" "${i}/meminfo" | awk '{print $4-4194304}')
	if [[ ${memavail} -lt 4194304 ]]; then
		echo "Not enough memory in numa node ${i}, skipping"
		continue
	fi
	cpulist=$(find "${i}" -name 'cpu[0-9]*' -printf '%f\n' | sed 's/cpu//' | sort -n)
	numcpu=$(echo "${cpulist}" | wc -w)
	if [[ ${numcpu} -lt 2 ]]; then
		allowedcpu=1
	else
		allowedcpu=$(( numcpu - 2 ))
	fi
	memtotest=$(( memavail / allowedcpu ))
	finalcpulist=$(echo "${cpulist}" | tail -n ${allowedcpu})
	for cpu in ${finalcpulist} ; do
		if [[ -f /sys/fs/cgroup/cgroup.controllers ]]; then
			systemd-run --scope --slice=-.slice --quiet taskset -c "${cpu}" numactl --membind "${nodenum}" "${MT}" "${memtotest}k" 1 > "/tmp/memtester.${node}.${cpu}.log" &
		else
			cgexec -g memory:/ -g cpuset:/ taskset -c "${cpu}" numactl --membind "${nodenum}" "${MT}" "${memtotest}k" 1 > "/tmp/memtester.${node}.${cpu}.log" &
		fi
		jobs="${jobs} ${!}"
	done
done

for i in ${jobs}; do
	if ! wait "${i}"; then
		echo "job ${i} failed, bailing out"
		cat /tmp/memtester.*.log
		exit 2
	fi
done

if [[ -s /var/log/mcelog ]]; then
        echo "MCE errors found, failing"
        cat /var/log/mcelog
	exit 2
fi

touch "/etc/storpool/${memchips}.memtested"

if [[ -s "${ipmitool}" ]]; then
    while IFS= read -r line;
    do
        event_epoch=$(echo "${line}" | date --utc -d "$(awk '{ print $3 " " $5 }')" +%s)
        if [[ $event_epoch -gt $epoch_start ]]; then
            echo "${line}" | grep -Ei 'memory|ecc|DIMM|correctable|uncorrectable' || true
        else
            break
        fi
    done < <(${ipmitool} sel list | tac)
fi
