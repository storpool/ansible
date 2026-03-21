#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: storpool_maintenance
short_description: Manage StorPool host maintenance mode via CLI
version_added: "1.0.0"
description:
    - This module sets or clears the maintenance mode for a specific host by executing the local 'storpool' command.
    - If 'node_id' is provided, it targets that node. Otherwise, it targets the current executing host (using SP_OURID).
options:
    state:
        description:
            - Whether to ensure the host is in maintenance mode or out of it.
        choices: [present, absent]
        default: present
        type: str
    node_id:
        description:
            - The specific StorPool node ID (integer) to target for maintenance.
            - If omitted, the module uses 'storpool_confshow SP_OURID' to target the current host.
        required: false
        type: int
    duration:
        description:
            - The duration for the maintenance window (e.g., '1h', '30m'). Required if state=present.
        type: str
    description:
        description:
            - A brief description for the maintenance task. Required if state=present.
        type: str
requirements:
    - The 'storpool' command-line tool must be installed on the target host.
'''

def execute_command(module, command, fail_on_rc=True):
    """Executes a storpool command and returns parsed JSON output or logs error."""
    rc, stdout, stderr = module.run_command(command)

    if rc != 0 and fail_on_rc:
        module.fail_json(msg=f"Command failed (RC: {rc}): {command}", stderr=stderr, stdout=stdout)

    if stdout:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            module.fail_json(msg=f"Failed to parse JSON output. Error: {e}", stdout=stdout, stderr=stderr)

    return {}

def get_local_node_id(module):
    """Executes storpool_confshow SP_OURID to get the current host's nodeId."""
    cmd = "storpool_confshow SP_OURID"
    rc, stdout, stderr = module.run_command(cmd)

    if rc == 0 and stdout:
        try:
            parts = stdout.strip().split('=')
            if len(parts) == 2 and parts[0] == 'SP_OURID':
                return int(parts[1])
            else:
                raise ValueError("Unexpected output format.")
        except ValueError as e:
            module.fail_json(msg=f"Failed to parse node ID from output: {stdout.strip()}",
                             details=f"Error: {e}")

    module.fail_json(msg="Failed to determine current host's SP_OURID (Node ID)",
                     stdout=stdout, stderr=stderr)


def get_current_state(module, storpool_path, target_node_id):
    """
    Checks if the specified target_node_id is in maintenance mode.
    """

    list_cmd = f"{storpool_path} -j maintenance list"

    rc, stdout, stderr = module.run_command(list_cmd)

    if rc == 0 and stdout:
        try:
            data = json.loads(stdout)
            nodes_data = data.get('data', {}).get('nodes', [])

            for node_entry in nodes_data:
                if node_entry.get('nodeId') == target_node_id:
                    return node_entry

        except json.JSONDecodeError as e:
            module.fail_json(msg=f"Failed to parse JSON from 'maintenance list'. Error: {e}", stdout=stdout)

    return None

def run_module():
    module_args = dict(
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        node_id=dict(type='int', required=False, default=None),
        duration=dict(type='str', required=False, default=None),
        description=dict(type='str', required=False, default=None),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    state = module.params['state']
    duration = module.params['duration']
    description = module.params['description']

    storpool_path = module.get_bin_path('storpool', required=True)

    target_id = module.params['node_id']
    if target_id is None:
        target_id = get_local_node_id(module)
        target_alias = 'here'
    else:
        target_alias = f"node {target_id}"

    current_maintenance = get_current_state(module, storpool_path, target_id)

    if state == 'present':
        if current_maintenance is not None:
            module.exit_json(changed=False, result=current_maintenance)
        else:
            if not duration or not description:
                module.fail_json(msg="Duration and description are required when state is 'present'")

            if module.check_mode:
                module.exit_json(changed=True, msg=f"Maintenance will be set on {target_alias} (check_mode)")

            cmd = f"{storpool_path} -j maintenance set {target_alias} duration {duration} description '{description}'"
            result = execute_command(module, cmd)

            module.exit_json(changed=True, result=result)

    elif state == 'absent':
        if current_maintenance is None:
            module.exit_json(changed=False, msg="Host is already out of maintenance.")
        else:
            if module.check_mode:
                module.exit_json(changed=True, msg=f"Maintenance will be cleared on {target_alias} (check_mode)")

            clear_cmd = f"{storpool_path} -j maintenance complete {target_alias}"
            execute_command(module, clear_cmd)

            module.exit_json(changed=True, msg="Maintenance successfully cleared.")

if __name__ == '__main__':
    run_module()