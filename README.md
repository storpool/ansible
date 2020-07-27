
StorPool ansible deployment
===========================

The repository contains a playbook for deploying storpool.

For now there is only one role.

It is still a work in progress, but should handle most deployments.

## Common usage:

```
ansible-playbook /path/to/playbook.yml [parameters]
```

### Common `ansible-playbook` parameters

| Parameter (Long) | Parameter (Short) | Parameter Description |
|--|--|--|
| --inventory | -i | specify inventory host path or comma separated host list |
| --limit | -l | further limit selected hosts to an additional pattern |
| --list-tags |  | list all available tags |
| --tags | -t | only run plays and tasks tagged with these values |
| --skip-tags |  | only run plays and tasks whose tags do not match these values |
| --step |  | one-step-at-a-time: confirm each task before running |


## Using role's tags:

```
# Show list of available tags:

ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --list-tags

# Run specific tags:

ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --tags network_validation

# Skip specific tags:

ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --skip-tags configure_network,init_drives,network_validation

# Run specific task on a specific server from your inventory:

ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --limit example-server.1 --tags configure_network

```

> **NOTE:** We use fact caching in order to speed up the process by caching all required variables on the ansible server (inside `./facts` directory) for later runs. If you have deleted the facts directory or any of the hosts facts inside it, you need to execute `ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --tags variables` in order for you to re-gather all required variables inside the facts cache.

## Using hosts facts:

```
# Gather all required playbook variables to cache:

ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --tags variables

# Flush facts cache and gather everything again:

ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --tags variables --flush-cache

```

## Work is needed for:

- better disk initialization
- tests of CPU settings (turbocheck)
- auto-enable storpool_nvmed if nvme drives have been initialized
- add integration roles (onapp, openstack, cloudstack opennebula, etc)
- ubuntu: more testing to address specific cases
