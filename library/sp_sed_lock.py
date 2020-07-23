#!/usr/bin/env python

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import ConfigParser
import subprocess
import os

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'StorPool'
}


DOCUMENTATION = '''
---
module: sp_sed_lock

short_description: Lock SED device by hdparm or sedutil

version_added: '2.7'

author:
    - Nikolay Tenev (nikolay.tenev@storpool.com)
'''


def main():
    # define the available arguments/parameters that a user can set
    module_args = dict(
        conf = dict(required=True, type='str'),
        drive = dict(required=True, type='str')
    )

    # seed the result dict in the object
    result = dict(
        changed=False,
        message=''
    )

    # the AnsibleModule object will be the abstraction working with Ansible
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False
    )

    # load the config
    config = ConfigParser.ConfigParser()
    config.readfp(open(module.params['conf']))

    # lock the device by type
    if module.params['drive'] in config.sections():
        sed_type = config.get(module.params['drive'], 'sed_type')
        sed_pass = config.get(module.params['drive'], 'sed_pass')

        if sed_type == 'opal':
            nvme_controller = os.path.realpath('/dev/disk/by-id/{}'.format(module.params['drive'])).rpartition('n')[0]

            try:
                result['message'] = subprocess.check_output(
                    ['/usr/sbin/sedutil-cli', '--initialSetup', sed_pass, nvme_controller],
                    shell=False
                )

            except Exception as e1:
                result['changed'] = False
                module.fail_json(msg='Exception: {}'.format(e1), **result)

            try:
                result['message'] = subprocess.check_output(
                    ['/usr/sbin/sedutil-cli', '--enableLockingRange', '0', sed_pass, nvme_controller],
                    shell=False
                )

            except Exception as e2:
                result['changed'] = False
                module.fail_json(msg='Exception: {}'.format(e2), **result)

            result['changed'] = True
            result['message'] = 'Device {} locked with OPAL key {}'.format(module.params['drive'], sed_pass)
            module.exit_json(**result)

        elif sed_type == 'atasf':

            try:
                result['message'] = subprocess.check_output(
                    ['/usr/sbin/hdparm', "--user-master", "u", "--security-set-pass", sed_pass, '/dev/disk/by-id/{}'.format(module.params['drive'])],
                    shell=False
                )

            except Exception as e3:
                result['changed'] = False
                module.fail_json(msg='Exception: {}'.format(e3), **result)

            result['changed'] = True
            result['message'] = 'Device {} locked with ATA key {}'.format(module.params['drive'], sed_pass)
            module.exit_json(**result)

        else:
            result['changed'] = False
            module.fail_json(msg='Unknown SED type {}'.format(sed_type), **result)

    else:
        result['changed'] = False
        result['message'] = 'Device {} not found in the config.'.format(module.params['drive'])
        module.fail_json(msg='SED locking fail', **result)

if __name__ == '__main__':
    main()
