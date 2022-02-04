initialize_disks
=========

Initializes disks to be used by StorPool server instances on the host.

Requirements
------------

StorPool server module to be installed.

Role Variables
--------------

| Variable name                   | Type    | Default value | Description |
| ------------------------------- | ------- |-------------- | ----------- |
| sp_new_cluster                  | Boolean | False         | Designates if this is the first deployment of the cluster. Sets an `-I` to the first disk of the first node. |
| sp_server_instances             | Integer | 1             | Sets the number of server instances to spread disks over |
| sp_min_disk_size                | String  | "960GB"       | Minimum size of SATA disks to be considered for initialization. Disks whose size is smaller than this will be excluded from the list |
| sp_max_disk_size                | String  | "14TB"        | Maximum size of SATA disks to be considered for initialization. Disks whose size is larger than this will be excluded from the list |
| sp_min_nvme_size                | String  | "100GB"       | Minimum size of NVMe devices to be considered for initialization. Please have in mind that raising this limit will exclude Optane NVMes from the list of discovered disks. |
| sp_min_pmem_size                | String  | "1GB"         | Minimum size of PMEM devices to be considered for initialization |
| sp_disk_offset                  | Integer | 0             | Used to generate StorPool disk IDs when there are nodes with IDs > 40 |
| sp_nvme_disk_id_offset          | Integer | 0             | Used to generate StorPool disk IDs for NVMe devices |
| sp_ssd_disk_id_offset           | Integer | 10            | Used to generate StorPool disk IDs for SSD devices |
| sp_hdd_disk_id_offset           | Integer | 20            | Used to generate StorPool disk IDs for HDD devices |
| sp_ssd_disk_init_args           | List    | []            | List of strings in the form of "--arg1,--arg2" that will be used to initialize SSD devices |
| sp_hdd_disk_init_args           | List    | []            | List of strings in the form of "--arg1,--arg2" that will be used to initialize HDD devices |
| sp_discover_disk_run            | Boolean | True          | Designates if the `disk_init_helper` tool should run its discover phase to collect a list with usable devices |
| disk_init_helper_discovery_file | String  | "/var/spool/storpool/disk-init-discovery.json" | Specifies a path to a JSON file containing the list of devices of to be initialized |
| sp_test_discovered_disks        | Boolean | True          | Only for SP testing lab use! Whether to test the disks found in the discovery phase of `disk_init_helper` |


Dependencies
------------

- add-storpool-repo role
- install-sp-python role

License
-------

Apache License 2.0

Author 
------

StorPool AD 2021.
