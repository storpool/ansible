configure_networking
=========

Configures host networking settings according to the network topology StorPool will be deployed with. 
WARNING! This role requires that host has StorPool software installed on it. Please ensure that this is the case prior
to running it.

Role Variables
--------------

Variables prefixed with `sp_` are defined as defaults and therefore can be overwritten at the inventory level.
Variables without the `sp_` prefix are set as role-level variables.

| Variable name                    | Type    | Default value        | Description |
| -------------------------------- | ------- | -------------------- | ----------- |
| sp_configure_network             | Boolean | False                | Controls whether network configuration should be generated and applied. |
| sp_force_network_reconfiguration | Boolean | False                | Controls whether network configuration should be applied if the host is already configured. |
| sp_bring_up_network              | Boolean | True                 | Controls whether configured network interfaces should be brought up. |
| sp_raw_interfaces                | String  | None                 | A pair of white space delimited interface names that are to be used as raw interfaces. |
| sp_mtu                           | String  | None                 | MTU of the raw interfaces to configure. |
| sp_vlan                          | Integer | None                 | VLAN ID to be used for StorPool storage data. If not set, the net_helper utility assumes untagged traffic. |
| sp_network                       | String  | None                 | Network prefix in the format of `A.B.C.D/E` designating the network to generate addresses from. |
| sp_network_mode                  | String  | `active-backup-bond` | The network mode that StorPool will work with. |
| sp_nm_controlled                 | Boolean | None                 | Controls whether network configuration should be applied via NetworkManager. |
| disable_network_acceleration     | Boolean | False                | Disables hardware-based acceleration. CAUTION! Do not set this without explicitly consulting with StorPool Support team. |
| sp_bond_name                     | String  | None                 | If defined, it sets the name of the bond interface to be used by StorPool. |
| sp_bridge_name                   | String  | None                 | If defined, it sets the name of the bridge interface to be used by StorPool. |
| sp_arp_ip_targets                | String  | None                 | Whitespace delimited list of IP addresses to be used as ARP IP targets. |
| sp_address_offset                | Int     | None                 | If defined, this will offset the IP address of each host by the amount specified. |
| sp_add_iface_net                 | List    | None                 | List of extra VLANs and IP addresses to be configured on the interfaces. |
| sp_addnet_address_offset         | Int     | None                 | If defined, this will offset the extra IP address of each host by the amount specified. |
| sp_iscsi_network_mode            | String  | None                 | If defined, it sets the network mode of the iSCSI raw interfaces. |
| sp_iscsi_mtu                     | Int     | None                 | If defined, sets the MTU of the iSCSI interfaces. By default it's set to 9000. |
| sp_iscsi_bond_name               | String  | None                 | If defined, sets the name of the bond interface which binds the two iSCSI raw interfaces. |
| sp_iscsi_bridge_name             | String  | None                 | If defined, sets the name of the bridge interface which sits on top of a bond used for iSCSI. |
| sp_iscsi_arp_ip_targets          | String  | None                 | Whitespace delimited list of IP addresses to be used as ARP IP targets for iSCSI bond. |
| sp_iscsi_address_offset          | Int     | None                 | If defined, this will offset the iSCSI OS IP address of each host by the amount specified. |
| sp_iscsicfg_net                  | List    | None                 | List of extra VLANs and IP addresses to be configured on the iSCSI interfaces. |


Example Playbook
----------------

The role generates, applies and validates network configuration for StorPool services. It requires that StorPool software
is installed prior to calling it. 
Variables `sp_raw_interfaces` and `sp_network` are required. 
The variable `sp_raw_interfaces` must contain two white-space separated interface names of at least two interfaces.
The variable `sp_network` must contain a network prefix in the format of `A.B.C.D/E`. IP addresses of nodes will be allocated
from this prefix.
If the host has an iSCSI service running on it, variables `sp_iscsi_raw_interfaces`, `sp_iscsi_network_mode` and `sp_iscsicfg_net`
are required. Variable `sp_iscsi_raw_interfaces` must contain two white-space separated interface names of at least two interfaces.
Variable `sp_iscsi_network_mode` controls the way the interfaces are organized. Variable `sp_iscsicfg_net` configures iSCSI OS
network configuration so that StorPool iSCSI can be pinged by the `storpool_stat` service.

Example without iSCSI service

Inventory example:

    hosts: node1
      sp_services:
        - mgmt
        - server
      sp_raw_interfaces: "sp0 sp1"
    vars:
      sp_vlan: 600
      sp_network: "10.60.0.0/24"

Playbook example

    - hosts: storpool
      pre_tasks:
        - name: Building in-memory inventory groups
          include_tasks: tasks/generate_group_membership.yml
      roles:
         - { role: storpool.configure_networking }


Example with iSCSI service

Inventory example:

    hosts: node1
      sp_services:
        - mgmt
        - server
        - iscsi
      sp_raw_interfaces: "sp0 sp1"
      sp_iscsi_raw_interfaces: "enp1s0f0 enp1s0f1"
    vars:
      sp_vlan: 600
      sp_network: "10.60.0.0/24"
    children:
      storpool_iscsi:
        hosts: {}
        vars:
          sp_iscsi_network_mode: "exclusive-ifaces"
          sp_iscsicfg_net:
            - "1401,10.140.1.0/24:1402,10.140.2.0/24"
          sp_iscsi_address_offset: 100

Playbook example

    - hosts: storpool
      pre_tasks:
        - name: Building in-memory inventory groups
          include_tasks: tasks/generate_group_membership.yml
      roles:
         - { role: storpool.configure_networking }


License
-------

Apache-2.0

Author 
------

StorPool AD 2022.
