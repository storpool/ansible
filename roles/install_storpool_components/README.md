install_storpool_components
=========

Installs all configured StorPool services and their required dependencies.

Role Variables
--------------

Variables prefixed with `sp_` are defined as defaults and therefore can be overwritten at the inventory level.
Variables without the `sp_` prefix are set as role-level variables.

| Variable name                 | Type    | Default value                       | Description |
| ----------------------------- | ------- | ----------------------------------- | ----------- |
| sp_tools_directory            | String  | `{{ ansible_user_dir }}/storpool`   | Directory where StorPool will place installation archives and extra tools used by the StorPool support team. |
| sp_configuration_path         | String  | `{{ inventory_dir }}/storpool.conf` | Path to the storpool.conf file on the Ansible controller. |
| sp_getpackage_url             | String  | See `defaults/main.yml`             | URL to the Python tool used to download StorPool release archives. |
| sp_install_helper_url         | String  | See `defaults/main.yml`             | URL to the Python tool used to install StorPool release archives. |
| sp_vault_url                  | String  | See `defaults/main.yml`             | URL to the binary repository to download StorPool release archives from. |
| sp_target_release             | String  | `release`                           | Release target from which to download the StorPool release archives from. |
| sp_getpackage_path            | String  | `{{ sp_tools_directory }}/getpackage.py` | Absolute path to the getpackage Python tool. |
| sp_install_method             | String  | `web`                               | Release method to be used to install StorPool. |
| sp_install_helper_path        | String  | `{{ sp_tools_directory }}/install_modules_helper.py` | Absolute path to the installation helper tool. |
| sp_reinstall                  | Boolean | False                               | Whether the installation helper tool should reinstall the packages. |
| sp_retry_install              | Boolean | True                                | Whether the installation helper tool should retry the installation. |
| sp_run_enable_grub_iommu      | Boolean | True                                | Whether the kernel should start the IOMMU. |
| sp_vm                         | Boolean | `{{ ansible_virtualization_role == 'guest' }}` | Whether the machine is a virtual one. |


Example Playbook
----------------

The role applies installs StorPool components based on the membership of the current host to a `storpool_` group. E.g. if
the host `node1` is part of the `storpool_mgmt` group, then host `node1` will have the `storpool_mgmt` service installed.
Membership of a group can be automatically configured using the `tasks/generate_group_membership.yml` tasks file. It examines
the elements in the `sp_servies` host variable and depending on the services listed there places the host in the appropriate
group like the example below:

Inventory example:

    hosts: node1
      sp_services:
        - mgmt

Playbook example

    - hosts: storpool
      pre_tasks:
        - name: Building in-memory inventory groups
          include_tasks: tasks/generate_group_membership.yml
      roles:
         - { role: storpool.boostrap_node, sp_target_release: release }

Membership of a group can be also described directly in the inventory like so:

    hosts: node1
    children:
      storpool_mgmt:
        hosts:
          node1

In this case, calling the role should suffice:

    - hosts: storpool
      roles:
         - { role: install_storpool_components, sp_target_release: release }


License
-------

Apache-2.0

Author 
------

StorPool AD 2022.
