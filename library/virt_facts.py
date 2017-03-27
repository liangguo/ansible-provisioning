#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2012 Dag Wieers <dag@wieers.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
author: Dag Wieers
module: virt_facts
short_description: Gather facts for a guest on libvirt
description:
  - This module gathers facts for a specific guest on a KVM host.
    These facts include hardware and network related information useful
    for provisioning (e.g. macaddress, uuid).
  - This module requires the libvirt python module.
version_added: "0.8"
options:
  host:
    description:
      - The KVM host the virtual server is located on.
  guest:
    description:
      - The virtual server to gather facts for on the KVM host.
    required: true
examples:
  - description: Task to gather facts from a KVM host only if the system is a KVM guest
    code: |
      action: virt_facts guest=$inventory_hostname_short
      delegate_to: $virthost
      only_if: "'$cmdb_hwmodel'.startswith('KVM')"
  - description: Typical output of virt_facts for a guest
    code:
    - hw_architecture: "i686"
      hw_boot: [ "hd" ]
      hw_eth0:
      - macaddress: "aa:bb:cc:dd:ee:ff"
        macaddress_dash: "aa-bb-cc-dd-ee-ff"
        source: "br0"
        type: "virtio"
      hw_eth1:
      - macaddress: "00:11:22:33:44:55"
        macaddress_dash: "00-11-22-33-44-55"
        source: "default"
        type: "virtio"
      hw_features: [ "acpi", "apic", "pae" ]
      hw_machine: "rhel5.4.0"
      hw_memtotal_mb: 1024
      hw_processor_count: 2
      hw_product_uuid: "8cde06d5-df87-2a13-125d-86fbcc3bcfcd"
      module_hw: true
notes:
  - This module ought to be run from a system that can access a KVM host directly.
    Either by using local_action, or using delegate_to.
'''

import sys

try:
    import xml.etree.ElementTree as ET
except ImportError:
    try:
        import elementtree.ElementTree as ET
    except ImportError:
        print "failed=True msg='ElementTree python module unavailable'"

try:
    import libvirt
except ImportError:
    print "failed=True msg='libvirt python module unavailable'"
    sys.exit(1)

def main():

    module = AnsibleModule(
        argument_spec = dict(
            host = dict(default='localhost'),
#            login = dict(required=True),
#            password = dict(required=True),
            guest = dict(required=True, aliases=['name', 'domain']),
        )
    )

    host = module.params.get('host')
#    login = module.params.get('login')
#    password = module.params.get('password')
    guest = module.params.get('guest')

    try:
        server = libvirt.open("qemu:///system")
    except libvirt.libvirtError, e:
        module.fail_json(msg=str(e))

    if not server:
        raise Exception("hypervisor connection failure")

    try:
        vm = server.lookupByName(guest)
    except libvirt.libvirtError, e:
        module.fail_json(msg=str(e))

    data = vm.XMLDesc(0)
    root = ET.fromstring(data)

    facts = {
        'module_hw': True,
        'hw_architecture': root.find('./os/type').attrib['arch'],
        'hw_boot': [ d.attrib['dev'] for d in root.findall('./os/boot') ],
        'hw_features': [ f.tag for f in root.find('./features') ],
        'hw_machine': root.find('./os/type').attrib['machine'],
        'hw_memtotal_mb': int(root.findtext('currentMemory'))/1024,
        'hw_processor_count': int(root.findtext('vcpu')),
        'hw_product_uuid': root.findtext('uuid'),
    }

    ifidx = 0
    for entry in root.findall('./devices/interface'):

        factname = 'hw_eth' + str(ifidx)
        facts[factname] = {
            'macaddress': entry.find('mac').attrib['address'],
            'macaddress_dash': entry.find('mac').attrib['address'].replace(':', '-'),
            'type': entry.find('model').attrib['type'],
        }

        if 'network' in entry.find('source').attrib.keys():
            facts[factname]['source'] = entry.find('source').attrib['network']
        elif 'bridge' in entry.find('source').attrib.keys():
            facts[factname]['source'] = entry.find('source').attrib['bridge']

        if entry.find('target'):
            if 'dev' in entry.find('target').attrib.keys():
                facts[factname]['target'] = entry.find('target').attrib['dev']

        ifidx += 1

    module.exit_json(ansible_facts=facts)

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
if __name__ == '__main__':
    main()
