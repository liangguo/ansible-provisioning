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
module: vbox_facts
short_description: Gather facts for a guest on VirtualBox
description:
  - This module gathers facts for a specific guest on a VirtualBox host.
    These facts include hardware and network related information useful
    for provisioning (e.g. macaddress, uuid).
  - This module requires the vboxapi python module.
version_added: "0.9"
options:
  host:
    description:
      - The VirtualBox host the virtual server is located on.
  login:
    description:
      - The login name to authenticate on the VirtualBox host.
  password:
    description:
      - The password to authenticate on the VirtualBox host.
  method:
    description:
      - The connection method to access the VirtualBox host.
    default: XPCOM
    choices: [ "MSCOM", "WEBSERVICE", "XPCOM" ]
  guest:
    description:
      - The virtual server to gather facts for on the VirtualBox host.
    required: true
examples:
  - description: Task to gather facts from a VirtualBox host only if the system is a VirtualBox guest
    code: |
      local_action: vbox_facts guest=$inventory_hostname_short
      only_if: "'$cmdb_hwmodel'.startswith('VirtualBox')"
  - description: Typical output of vbox_facts for a guest
    code:
    - hw_chipset: "PIIX3"
      hw_description: "Test system for QA"
      hw_eth0:
      - adaptertype: "Virtio"
        connected: true
        label": "intnet"
        macaddress: "08:00:27:1B:79:C1"
        macaddress_dash: "08-00-27-1B-79-C1"
        type: "Internal"
      hw_eth1:
      - adaptertype: "Virtio"
        connected: true
        label: ""
        macaddress: "08:00:27:9A:3C:45"
        macaddress_dash: "08-00-27-9A-3C-45"
        type: "NAT"
      hw_firmware: "EFI"
      hw_memtotal_mb: 512
      hw_ostype: "RedHat_64"
      hw_processor_count: 1
      hw_product_uuid: "7af47453-939b-4d42-9fc9-3feb229a92b5"
      hw_state: "Saved"
      hw_uuid: "7af47453-939b-4d42-9fc9-3feb229a92b5"
      hw_version: "2"
      module_hw: true
notes:
  - This module ought to be run from a system that can access a VirtualBox host directly.
    Either by using local_action, or using delegate_to.
'''

import sys

try:
    import vboxapi
except ImportError:
    print "failed=True msg='vboxapi python module unavailable'"
    sys.exit(1)


def main():

    module = AnsibleModule(
        argument_spec = dict(
            host = dict(default=None, aliases=['url']),
            method = dict(default='XPCOM', choices=['MSCOM', 'XPCOM', 'WEBSERVICE']),
            login = dict(default=None, aliases=['user']),
            password = dict(default=None),
            guest = dict(required=True, aliases=['name']),
        )
    )

    host = module.params.get('host')
    method = module.params.get('method')
    login = module.params.get('login')
    password = module.params.get('password')
    guest = module.params.get('guest')

    try:
        mgr = vboxapi.VirtualBoxManager(method, { 'url': host, 'user': login, 'password': password })
    except Exception, e:
        module.fail_json(msg=str(e))

    vbox = mgr.vbox
    try:
        vm = vbox.findMachine(guest)
    except Exception, e:
        module.fail_json(msg=e.msg)

    vbc = vboxapi.VirtualBox_constants.VirtualBoxReflectionInfo(False)

    # FIXME: There must be a better way
    ChipsetTypes = [v for k, v in sorted([(v, k) for k, v in vbc.all_values('ChipsetType').iteritems()])]
    FirmwareTypes = [v for k, v in sorted([(v, k) for k, v in vbc.all_values('FirmwareType').iteritems()])]
    MachineStates = [v for k, v in sorted([(v, k) for k, v in vbc.all_values('MachineState').iteritems()])]
    ArchitectureTypes = [ 'i686', 'x86_64' ]
    facts = {
        'module_hw': True,
        'hw_architecture': ArchitectureTypes[vbox.getGuestOSType(vm.OSTypeId).is64Bit],
        'hw_chipset': ChipsetTypes[vm.chipsetType],
        'hw_description': vm.description,
        'hw_firmware': FirmwareTypes[vm.firmwareType],
#        'hw_groups': vm.groups,
        'hw_memtotal_mb': vm.memorySize,
#        'hw_name': vm.name,
        'hw_ostype': vm.OSTypeId,
        'hw_processor_count': vm.CPUCount,
        'hw_product_uuid': vm.hardwareUUID,
        'hw_state': MachineStates[vm.state],
        'hw_uuid': vm.id,
        'hw_version': vm.hardwareVersion,
    }

    # FIXME: There must be a better way
    NetworkAdapterTypes = [v for k, v in sorted([(v, k) for k, v in vbc.all_values('NetworkAdapterType').iteritems()])]
    NetworkAttachmentTypes = [v for k, v in sorted([(v, k) for k, v in vbc.all_values('NetworkAttachmentType').iteritems()])]
    for ifidx in range(0, vbox.systemProperties.getMaxNetworkAdapters(vm.chipsetType)):
        entry = vm.getNetworkAdapter(ifidx)

        if not entry.enabled: continue

        factname = 'hw_eth' + str(ifidx)
        facts[factname] = {
            'adaptertype': NetworkAdapterTypes[entry.adapterType],
            'connected': entry.cableConnected,
            'macaddress': ':'.join([entry.MACAddress[i:i+2] for i in range(0, 12, 2)]),
            'macaddress_dash': '-'.join([entry.MACAddress[i:i+2] for i in range(0, 12, 2)]),
#            'speed': entry.lineSpeed,
            'type': NetworkAttachmentTypes[entry.attachmentType],
        }
        if entry.attachmentType == 1:
            facts[factname]['label'] = entry.NATNetwork
        elif entry.attachmentType == 2:
            facts[factname]['label'] = entry.bridgedInterface
        elif entry.attachmentType == 3:
            facts[factname]['label'] = entry.internalNetwork
        elif entry.attachmentType == 4:
            facts[factname]['label'] = entry.hostOnlyInterface
        elif entry.attachmentType == 5:
            facts[factname]['label'] = entry.genericDriver,
        else:
            facts[factname]['label'] = ''

    module.exit_json(ansible_facts=facts)

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
if __name__ == '__main__':
    main()
