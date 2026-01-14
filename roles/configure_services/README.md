configure_services
=========

This role configures systemd to enable and start the required service units for StorPool to work as expected.

Requirements
------------

The StorPool software must already be installed via the `install_storpool_components` role.

Role Variables
--------------

Variables prefixed with `sp_` are defined as defaults and therefore can be overwritten at the inventory level.
Variables without the `sp_` prefix are set as role-level variables.

| Variable name                    | Type    | Default value           | Description                                        |
|----------------------------------|---------|-------------------------|----------------------------------------------------|
| sp_start_services                | Boolean | True                    | Start all installed StorPool services on the  host |

Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    -   hosts: storpool_block,storpool_server,storpool_mgmt,storpool_iscsi,storpool_bridge
        roles:
            - configure_services

License
-------

Apache-2.0

Author 
------

StorPool AD 2022.
