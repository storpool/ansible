#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
from ansible.module_utils.basic import AnsibleModule

# --- DOCUMENTATION ---
DOCUMENTATION = '''
---
module: storpool_disk
short_description: Gather StorPool disk inventory facts via storpool_initdisk
version_added: "1.0.0"
description:
    - Gathers detailed inventory facts about all local disks, including their StorPool initialization status.
options:
    storpool_only:
        description:
            - If set to true, only includes disks where the 'isStorPool' flag is true.
        required: false
        type: bool
        default: False
    nvme_only:
        description:
            - If set to true, only includes disks where the 'nvme' flag is true (NVMe drives).
        required: false
        type: bool
        default: False
requirements:
    - The 'storpool_initdisk' command-line tool must be installed on the target host.
'''

# --- HELPER FUNCTIONS ---

def get_full_inventory(module, initdisk_path):
    """
    Executes storpool_initdisk -l --json and returns the full parsed JSON data.
    """
    list_cmd = f"{initdisk_path} -l --json"

    rc, stdout, stderr = module.run_command(list_cmd, check_rc=True)

    if not stdout:
        module.fail_json(msg="storpool_initdisk returned empty output.", stdout=stdout, stderr=stderr)

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        module.fail_json(msg="Failed to parse JSON from storpool_initdisk -l.", stdout=stdout)

    return None # Unreachable


def run_module():
    module_args = dict(
        storpool_only=dict(type='bool', default=False),
        nvme_only=dict(type='bool', default=False), # New argument definition
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    storpool_only = module.params['storpool_only']
    nvme_only = module.params['nvme_only'] # Retrieve the new parameter

    # 1. Find the required tool
    initdisk_path = module.get_bin_path('storpool_initdisk', required=True)

    # 2. Get the raw inventory data
    list_data = get_full_inventory(module, initdisk_path)
    raw_disks = list_data.get('disks', {})

    # 3. Apply Filtering Logic

    # Start with all disks
    filtered_disks = raw_disks

    # Filter 1: storpool_only
    if storpool_only:
        filtered_disks = {
            dev: data
            for dev, data in filtered_disks.items()
            if data.get('isStorPool') is True
        }

    # Filter 2: nvme_only
    if nvme_only:
        filtered_disks = {
            dev: data
            for dev, data in filtered_disks.items()
            if data.get('nvme') is True
        }

    # 4. Return Facts to Ansible
    module.exit_json(
        changed=False,
        msg=f"Disk inventory collected (StorPool only: {storpool_only}, NVMe only: {nvme_only}).",
        storpool_disk_inventory=filtered_disks,
        raw_data=list_data
    )

# --- ENTRY POINT ---
if __name__ == '__main__':
    run_module()