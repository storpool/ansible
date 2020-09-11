StorPool Ansible Playbook
===========================

The repository contains StorPool's playbook and roles for Ansible.

### Common ansible-playbook usage

```
# Running this playbook with ansible-playbook:
ansible-playbook /home/tools/ansible/playbook.yml [parameters]
```

```
# This playbook can be also execuded directly from the playbook's directory, like this:
/home/tools/ansible/playbook.yml [parameters]
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
| --flush-cache |  | clear the fact cache for every host in inventory |

## Configuration

```
# Copy the hosts.example file:
cp hosts.example ansible.hosts
```

```
# Edit the hosts file and configure StorPool parameters:
vi ansible.hosts
```

```
# Save the file and run the playbook:
ansible-playbook /home/tools/ansible/playbook.yml -i ansible.hosts

# Or run it directly:
/home/tools/ansible/playbook.yml -i ansible.hosts
```

## Available Tags

| Tag | Description |
|--|--|
| variables | Set common variables for target hosts |
| dependencies | Install StorPool's dependencies on target hosts |
| system-tune | OS related configurations and performance tuning tasks |
| install | Download and install StorPool and the StorPool support tools |
| setup-network | Configure and validate StorPool's network |
| setup-drives | Initialize StorPool drives |
| configure-cgroups | Configure cgroups as per StorPool's requirements |
| finalise | Final configurations - generate VF configuration, enable storpool systemd services |
| reboot-hosts | Reboot target hosts |

```
# Show list of available tags:
ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --list-tags
```

```
# Run specific tags:
ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --tags network_validation
```

```
# Skip specific tags:
ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --skip-tags configure_network,init_drives,network_validation
```

```
# Run specific task on a specific server from your inventory:
ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --limit example-server.1 --tags configure_network
```

> **NOTE:** We use fact caching in order to speed up the process by caching all required variables on the ansible server (inside `./facts` directory) for later runs. If you have deleted the facts directory or any of the hosts facts inside it, you need to execute `ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --tags variables` in order for you to re-gather all required variables inside the facts cache.

## Roles variables


### Cluster data (variables under `[storpool:vars]` block)
| Variable | Description |
|--|--|
| sp_cluster | This is the top directory where Ansible configuration is saved. Usually `basename  $(pwd)` |
| sp_custdir | The parent directory of `sp_cluster`. This is `dirname  $(pwd)` |
| sp_toolsdir | The path on the destination hosts where StorPool files will be stored ***Defaults to `/root/storpool`*** |
| sp_release_file | Full path the StorPool tar.gz archive, or `web` to download it from StorPool's repo ***Defaults to web***|
| sp_release | StorPool version to be deployed (if sp_release_file='web')  ***Defaults to `19.01`*** |
| sp_new_cluster | Deployment type ***Defaults to True*** |
| sp_config | Path to storpool.conf on the ansible host ***Defaults to the inventory directory (Where the ansible inventory file is located)*** |
| sp_update_system | Perform OS update (yum/apt update/upgrade) on target hosts ***Defaults to True*** |
| sp_configure_network | Automatically configure network interfaces based on storpool.conf variables ***Defaults to False*** |
| sp_overwrite_iface_conf | Overwrite existing ineterface configuration files (iface-genconf -o). ***Defaults to False*** |
| sp_selinux | Set SELinux state (valid options are "permissive" or "disabled") ***Defaults to `disabled`*** |
| sp_disable_nm | Stop and disable NetworkManager ***Defaults to True*** |
| sp_disable_fw | Stop and disable firewalld/ufw (if False, will add ports for StorPool) ***Defaults to True*** |
| sp_vm | Nodes are virtual machines - It will be determined automatically if not specifically set |
| sp_summary_wait | Generate a summary and pause after variable validation ***Defaults to True*** |
| sp_reboot | Reboot node after deployment ***Defaults to False*** |
| sp_drive_erase | Init the drives even if they contain partitions (use with caution) ***Defaults to False*** |
| sp_cg_conf_extra | List of arguments to pass to storpool_cg conf |
| sp_diskid_offset |  Offset to calculate diskid prefix (useful when sp_node_id >= 40) |

> For more information please check hosts.example file    

## Using hosts facts

```
# Gather all required playbook variables to cache:
ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --tags variables
```

```
# Flush facts cache and gather everything again:
ansible-playbook /path/to/ansible/playbook.yml --inventory ansible.hosts --tags variables --flush-cache
```

## Work is needed for:

- Better disk initialization
- Tests of CPU settings (turbocheck)
- Auto-enable storpool_nvmed if nvme drives have been initialized
- Add integration roles (onapp, openstack, cloudstack opennebula, etc)
- Ubuntu: more testing to address specific cases
