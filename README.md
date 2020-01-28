StorPool ansible deployment
===========================

The repository contains a playbook for deploying storpool.
For now there is only one role.
It is still a work in progress, but should handle most deployments.

Work is needed for:

- better disk initialization
- tests of CPU settings (turbocheck)
- auto-enable storpool_nvmed if nvme drives have been initialized
- add integration roles (onapp, openstack, cloudstack opennebula, etc)
- ubuntu: more testing to address specific cases
