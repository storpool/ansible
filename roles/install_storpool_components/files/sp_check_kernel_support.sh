#!/bin/bash

sp_version="$1"
if [[ -z $sp_version ]]; then
        echo "Usage: $0 <sp_version>"
        echo "Exits with 1 if the SP version does NOT support the currently running kernel."
        exit 5
fi

kernel=$(uname -r)
sp_tar=$(ls -1t /root/storpool/storpool-${sp_version}*.tar.gz | head -n1)
sp_folder=${sp_tar##*/}
sp_folder=${sp_folder%-debug.tar.gz}
sp_folder=${sp_folder%.tar.gz}

supported_kernels=$(tar -xf "$sp_tar" "$sp_folder/kernel-versions.txt" -O)
if [[ $? -ne 0 ]]; then
        echo "Failed to read supported kernel versions in $sp_tar"
        exit 5
fi

if  echo "$supported_kernels" | grep -q "$kernel"; then
        echo "Kernel $kernel supported by $sp_tar, do not reboot"
        exit 0
else
        echo "Kernel $kernel NOT supported by $sp_tar, REBOOT"
        exit 1
fi
