#!/bin/bash

package="$1"
version="$2"
if [[ -z $version ]]; then
    echo "Usage: $0 <package_name> <desired_version>"
fi

for pver in $(rpm -q "$package" --qf '%{version}-%{release}\n'); do
    rpmdev-vercmp "$version" "$pver" &>/dev/null
    rc="$?"
    if [[ $rc -eq 12 ]]; then
        echo "downgrade"
        exit 1
    fi
done