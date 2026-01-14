configure_cgroups
=========

This role configures Linux CGroups to allocate and preserve the required amount of CPU cores and memory for StorPool to work as expected.

Requirements
------------

The StorPool software must already be installed via the `install_storpool_components` role.

Role Variables
--------------

Variables prefixed with `sp_` are defined as defaults and therefore can be overwritten at the inventory level.
Variables without the `sp_` prefix are set as role-level variables.

| Variable name                    | Type    | Default value           | Description |
| -------------------------------- |---------|-------------------------| ----------- |
| sp_cgtool_bin                    | String  | `/usr/sbin/storpool_cg` | Path to the StorPool cgtool executable |
| sp_cg_conf_extra                 | String  | ""                      | Extra arguments to pass to the StorPool cgtool |
| sp_cg_start_cgconfig             | Boolean | True                    | Apply the generated CGroup configuration by starting the `cgconfig` systemd service |
| sp_cg_hyperconverged             | Boolean | False                   | Configure the host as a hyperconverged node |


Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: servers
      roles:
         - configure_cgroups

License
-------

Apache-2.0

Author 
------

StorPool AD 2022.
