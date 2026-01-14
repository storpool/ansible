configure_sed
=========

This role configures encryption on drives that support it.

Requirements
------------

The StorPool software must already be installed via the `install_storpool_components` role.

Role Variables
--------------

Variables prefixed with `sp_` are defined as defaults and therefore can be overwritten at the inventory level.
Variables without the `sp_` prefix are set as role-level variables.


Example Playbook
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: storpool_servers
      roles:
         - configure_sed

License
-------

Apache-2.0

Author 
------

StorPool AD 2022.
