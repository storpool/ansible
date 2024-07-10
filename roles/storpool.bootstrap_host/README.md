bootstrap_node
=========

Installs all software dependencies and configures a host according to StorPools' requirements

Role Variables
--------------

Variables prefixed with `sp_` are defined as defaults and therefore can be overwritten at the inventory level.
Variables without the `sp_` prefix are set as role-level variables.

| Variable name                   | Type    | Default value                 | Description |
| ------------------------------- | ------- | ----------------------------- | ----------- |
| sp_upgrade_os                   | Boolean | `False`                       | Performs distribution-wide upgrade of all packages. |
| sp_selinux_disable              | Boolean | `True`                        | Disables SELinux on RHEL-like distributions. |
| common_packages                 | List    | See `vars/main.yml `          | List of package names to be installed common to all Linux distributions. |
| rc_local_commands               | List    | See `vars/main.yml `          | List of commands to be placed in `/etc/rc.local` and executed at boot. |
| distribution_packages           | List    | See `vars/redhat,debian.yml`  | List of package names common to all versions of the given distribution family. |
| centos_7_packages               | List    | See `vars/redhat.yml`         | List of package names to be installed on CentOS 7. |
| almalinux_8_packages            | List    | See `vars/redhat.yml`         | List of package names to be installed on AlmaLinux 8. |
| rockylinux_8_packages           | List    | See `vars/redhat.yml`         | List of package names to be installed on RockyLinux 8. |
| tuned_profile                   | String  | `throughput-performance`      | Sets the tuned profile on RHEL-like distributions. |
| ubuntu_18_packages              | List    | See `vars/debian.yml`         | List of package names to be installed on Ubuntu 18.04 . |
| ubuntu_20_packages              | List    | See `vars/debian.yml`         | List of package names to be installed on Ubuntu 20.04 . |

Example Playbook
----------------

The role applies configuration common to all hosts participating in a StorPool cluster. It is intended to be used like so:

    - hosts: storpool_nodes
      roles:
         - { role: storpool.boostrap_node, sp_upgrade_os: yes }

License
-------

Apache-2.0

