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
module: vsphere_facts
short_description: Gather facts for a guest on VMWare vSphere
description:
  - This module gathers facts for a specific guest on VMWare vSphere.
    These facts include hardware and network related information useful
    for provisioning (e.g. macaddress, uuid).
  - This module requires the pysphere python module.
version_added: "0.8"
options:
  host:
    description:
      - The vSphere server from the cluster the virtual server is located on.
    required: true
  login:
    description:
      - The login name to authenticate on the vSphere cluster.
    required: true
  password:
    description:
      - The password to authenticate on the vSphere cluster.
    required: true
  guest:
    description:
      - The virtual server to gather facts for on the vSphere cluster.
    required: true
examples:
  - description: Task to gather facts from a vSphere cluster only if the system is a VMWare guest
    code: |
      - local_action: vsphere_facts host=$esxserver login=$esxlogin password=$esxpassword guest=$inventory_hostname_short
        only_if: "'$cmdb_hwmodel'.startswith('VMWare ')
  - description: Typical output of a vsphere_facts run on a guest
    code:
      - hw_eth0:
        - addresstype: "assigned"
          label: "Network adapter 1"
          macaddress: "00:11:22:33:44:55"
          macaddress_dash: "00-11-22-33-44-55"
          summary: "VLAN-321"
        hw_guest_full_name: "Red Hat Enterprise Linux 6 (64-bit)"
        hw_guest_id: "rhel6_64Guest"
        hw_memtotal_mb: 2048
        hw_name: "centos6"
        hw_processor_count: 1
        hw_product_uuid: "ef50bac8-2845-40ff-81d9-675315501dac"
notes:
  - This module ought to be run from a system that can access vSphere directly.
    Either by using local_action, or using delegate_to.
'''

import sys
try:
    import pysphere
except ImportError:
    print "failed=True msg='pysphere python module unavailable'"
    sys.exit(1)

def main():

    module = AnsibleModule(
        argument_spec = dict(
            host = dict(required=True),
            login = dict(required=True),
            password = dict(required=True),
            guest = dict(required=True, aliases=['name']),
        )
    )

    host = module.params.get('host')
    login = module.params.get('login')
    password = module.params.get('password')
    guest = module.params.get('guest')

    server = pysphere.VIServer()
    try:
#        server.connect(host, login, password, trace_file='debug.txt')
        server.connect(host, login, password)
    except Exception, e:
        module.fail_json(msg='Failed to connect to %s: %s' % (host, e))

    try:
        vm = server.get_vm_by_name(guest)
    except pysphere.resources.vi_exception.VIException, e:
        module.fail_json(msg=e.message)

    data = vm.get_properties()
    facts = {
        'module_hw': True,
        'hw_name': vm.properties.name,
        'hw_guest_full_name':  vm.properties.config.guestFullName,
        'hw_guest_id': vm.properties.config.guestId,
        'hw_product_uuid': vm.properties.config.uuid,
        'hw_processor_count': vm.properties.config.hardware.numCPU,
        'hw_memtotal_mb': vm.properties.config.hardware.memoryMB,
    }

    ifidx = 0
    for entry in vm.properties.config.hardware.device:

        if not hasattr(entry, 'macAddress'): continue

        factname = 'hw_eth' + str(ifidx)
        facts[factname] = {
            'addresstype': entry.addressType,
            'label': entry.deviceInfo.label,
            'macaddress': entry.macAddress,
            'macaddress_dash': entry.macAddress.replace(':', '-'),
            'summary': entry.deviceInfo.summary,
        }

        ifidx += 1

    server.disconnect()
    module.exit_json(ansible_facts=facts)

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
if __name__ == '__main__':
    main()
