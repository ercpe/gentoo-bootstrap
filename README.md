gentoo-bootstrap
================

Tool to ease the creation of Gentoo Xen domU's. It's based on the idea to automate all the steps from a typical [stage3 installation](http://www.gentoo.org/doc/en/handbook/index.xml).


**This project is currently under heavy development. Expect all kinds of troubles!**



## Configuration

`gentoo-bootstrap` uses configuration files in `/etc/gentoo-bootstrap`. Currently, there is no way to specify values other than domU name and FQDN at the command line. An interactive prompt may be added later.

As a bare minimum you want the following settings:

    [DEFAULT]
    inherit = storage-simple.cfg
    
    [system]
    kernel = /boot/vm-kernel
    arch = amd64
    locales = en_GB.UTF-8 UTF-8,en_US.UTF-8 UTF-8, de_DE.UTF-8 UTF-8
    timezone = Europe/Berlin
    memory = 1024
    vcpu = 4

    [storage]
    layout = simple
    type = lvm
    volume_group = vg-name

    [network]
    config = auto
    bridge = br0

if you prefer (or have to use) static network configuration, change the `[network]` block to 

    [network]
    config = 192.168.12.34/24
    gateway = 192.168.12.1
    dns_servers = 192.168.12.1, 8.8.8.8, 8.8.4.4
    bridge = br0

You can use the `resolv_domain` and `resolv_search` options to specify the default domain and the dns search list.

A more advanced configuration file is shipped as the `sample.cfg` in the tarball.

### Defining custom storage

You propably noticed the `inherit = storage-simple.cfg` option in the `[DEFAULT]` block. This option automatically loads the file storage-simple.cfg into the current configuration file.

    [storage_simple]
    disks = 2
    disk0_mount = /
    disk0_size = 20G
    disk0_fs = ext4
    disk0_name = %(name)s-hdd0
    disk0_device = /dev/xvda1
    disk1_mount =
    disk1_size = 512M
    disk1_fs = swap
    disk1_name = %(name)s-swap
    disk1_device = /dev/xvda2
    
The storage_simple block defines a standard layout and is referenced by the `layout = simple` option in the `[storage]` block.

To create a custom virtual hard disk schema, create a custom `[storage_foo]` block following the same schema as `storage_simple` and reference it via the `layout` option in the main `[storage]` block.