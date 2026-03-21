#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import re
from ansible.module_utils.basic import AnsibleModule

# --- HELPER FUNCTIONS ---

def filter_storpool_stderr(stderr):
    """
    Removes known harmless warnings from stderr.
    """
    if not stderr:
        return ""
    # Filter out srcversion mismatch and reboot warnings
    lines = stderr.splitlines()
    filtered = [
        line for line in lines
        if "Mismatch between installed and loaded srcversion" not in line
        and "Please schedule a reboot" not in line
    ]
    return "\n".join(filtered).strip()

def get_running_status(module, ctl_path, target):
    """
    Checks the running status. Handles noise on stderr gracefully.
    """
    status_cmd = f"{ctl_path} status -j"

    # We don't use check_rc=True here because warnings might cause a non-zero RC
    rc, stdout, stderr = module.run_command(status_cmd)

    clean_stderr = filter_storpool_stderr(stderr)

    # If there is a real error (no stdout and leftover stderr)
    if rc != 0 and not stdout and clean_stderr:
        module.fail_json(msg="storpool_ctl status failed", stdout=stdout, stderr=clean_stderr)

    if not stdout:
        module.fail_json(msg="status command returned empty output.", stderr=clean_stderr)

    try:
        status_data = json.loads(stdout)
    except json.JSONDecodeError:
        module.fail_json(msg="Failed to parse JSON from status output.", stdout=stdout, stderr=clean_stderr)

    if target == 'servers':
        target_services = {k: v for k, v in status_data.items() if k.startswith('storpool_server')}
        if not target_services:
            return False
        return all(state == 'running' for state in target_services.values())
    else:
        return all(state == 'running' for state in status_data.values())

def parse_multi_json(module, stdout):
    """
    Parses stdout that contains multiple concatenated JSON objects.
    """
    transition_data = {}
    if stdout:
        for line in stdout.strip().split('\n'):
            if line.strip():
                try:
                    transition_data.update(json.loads(line))
                except json.JSONDecodeError:
                    continue # Skip non-json noise
    return transition_data

def run_module():
    module_args = dict(
        state=dict(type='str', choices=['started', 'stopped', 'enabled', 'disabled'], required=True),
        target=dict(type='str', choices=['all', 'servers'], default='all'),
        force=dict(type='bool', default=False),
        wait_for_disks=dict(type='bool', default=False),
        wait_seconds=dict(type='int', default=300),
        expose_nvme=dict(type='bool', default=False),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    state = module.params['state']
    target = module.params['target']

    RUNNING_ACTION_MAP = {'started': 'start', 'stopped': 'stop'}
    BOOT_ACTION_MAP = {'enabled': 'enable', 'disabled': 'disable'}

    if target == 'servers' and state not in RUNNING_ACTION_MAP:
        module.fail_json(msg="Target 'servers' is only valid for started/stopped states.")

    ctl_path = module.get_bin_path('storpool_ctl', required=True)

    # --- HANDLE RUNNING STATES ---
    if state in RUNNING_ACTION_MAP:
        is_running = get_running_status(module, ctl_path, target)
        action_verb = RUNNING_ACTION_MAP[state]

        action_needed = (state == 'started' and not is_running) or \
                        (state == 'stopped' and is_running)

        if action_needed:
            if module.check_mode:
                module.exit_json(changed=True, msg=f"Would {action_verb} services (check_mode)")

            cmd = f"{ctl_path} {action_verb}"
            if module.params['force']: cmd += " --force"
            if target == 'servers': cmd += " --servers"
            if state == 'started' and module.params['wait_for_disks']:
                cmd += f" --wait --seconds {module.params['wait_seconds']}"
            elif state == 'stopped' and module.params['expose_nvme']:
                cmd += " --expose-nvme"
            cmd += " -b -j"

            rc, stdout, stderr = module.run_command(cmd)
            clean_stderr = filter_storpool_stderr(stderr)

            # Fail only if there is real stderr left after filtering noise
            if rc != 0 and clean_stderr:
                module.fail_json(msg=f"Command '{action_verb}' failed", stdout=stdout, stderr=clean_stderr)

            transition_data = parse_multi_json(module, stdout)
            module.exit_json(
                changed=True,
                status_transitions=transition_data,
                msg=f"Services {state} successfully.",
                warnings=[stderr] if "Mismatch" in stderr else []
            )
        else:
            module.exit_json(changed=False, msg=f"Services already {state}.")

    # --- HANDLE BOOT STATES ---
    elif state in BOOT_ACTION_MAP:
        action_verb = BOOT_ACTION_MAP[state]
        if module.check_mode:
            module.exit_json(changed=True, msg=f"Would {action_verb} boot state (check_mode)")

        cmd = f"{ctl_path} {action_verb} -b -j"
        if module.params['force']: cmd += " --force"

        rc, stdout, stderr = module.run_command(cmd)
        clean_stderr = filter_storpool_stderr(stderr)

        if rc != 0 and clean_stderr:
            module.fail_json(msg=f"Set boot {state} failed", stdout=stdout, stderr=clean_stderr)

        transition_data = parse_multi_json(module, stdout)
        module.exit_json(changed=bool(transition_data), status_transitions=transition_data, msg=f"Boot state set to {state}.")

if __name__ == '__main__':
    run_module()