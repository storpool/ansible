#!/usr/bin/env python

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import ConfigParser
import os
import re
import subprocess

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'StorPool'
}


DOCUMENTATION = '''
---
module: sp_sed_classify

short_description: Classify device SED support

version_added: '2.7'

author:
    - Nikolay Tenev (nikolay.tenev@storpool.com)
'''

RE_HDPARM_SECURITY = re.compile(
    r""" ^
    # Some hdparm output
    .*

    # Start the "Security" section
    ^ Security: \s* \n

    # Expect the "Master password revision code" line first
    \t Master \s password [^\n]* \n

    # Skip any other lines in the same section (indented with one or more tabs)
    (?: \t [^\n]* \n )*?

    # Expect the "supported" feature to be enabled (not "\t not \t supported")
    \t \t supported \n

    # The rest of the hdparm output
    .*
    $ """,
    re.X | re.M | re.S,
)


def isValidATASF(drive):
    """Check the output of hdparm to figure stuff out."""
    output = subprocess.check_output(
        ['/usr/sbin/hdparm', '-I', drive],
        shell=False
    )

    return bool(RE_HDPARM_SECURITY.match(output))

def isValidOPAL(drive):
    nvme_controller = os.path.realpath(drive).rpartition('n')[0]

    output = subprocess.check_output(
        ['/usr/sbin/sedutil-cli', '--isValidSED', nvme_controller],
        shell=False
    )

    if output.startswith('/dev/nvme0 SED'):
        return True

    else:
        return False

def main():
    # define the available arguments/parameters that a user can set
    module_args = dict(
        drives = dict(required=True, type='str'),
        facts = dict(required=True, type='dict')
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

    sed_types = {
        'opal': list(),
        'atasf': list(),
#        'miss': list()
    }

    for drive in module.params['drives'].split(','):

        if drive in module.params['facts']:

            for link in module.params['facts'][drive]:

                if link.startswith('ata-') and isValidATASF(drive='/dev/disk/by-id/{0}'.format(link)):
                    sed_types['atasf'].append(link) 

                elif link.startswith('nvme-') and not link.startswith('nvme-eui') and isValidOPAL(drive='/dev/disk/by-id/{0}'.format(link)):
                    sed_types['opal'].append(link)   

#                else:
#                    sed_types['miss'].append(link)

    result = dict(sed_types)

    module.exit_json(**result) 

if __name__ == '__main__':
    main()
