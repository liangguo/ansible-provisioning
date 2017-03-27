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
module: vsphere_boot
short_description: Boot VMWare virtual machine using specific boot media
description:
  - 'This module boots a VMWare virtual machine through vSphere. The boot media
    can be one of: cd, fd or net.'
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
notes:
  - This module ought to be run from a system that can access vSphere directly.
    Either by using C(local_action), or C(using delegate)_to.
'''

import sys
import time
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
            guest = dict(required=True),
            force = dict(),
            match = dict(),
            media = dict(default=None, choices=['cd', 'fd', 'hd', 'net']),
            image = dict(),
            state = dict(choices=['boot_once', 'boot_always', 'no_boot', 'connect', 'disconnect', 'poweroff']),
        )
    )


    host = module.params.get('host')
    login = module.params.get('login')
    password = module.params.get('password')
    guest = module.params.get('guest')
    force = module.boolean(module.params.get('force'))
    match = module.params.get('match')
    media = module.params.get('media')
    image = module.params.get('image')
    state = module.params.get('state')

    server = pysphere.VIServer()
    try:
#        server.connect(host, login, password, trace_file='debug.txt')
        server.connect(host, login, password)
    except Exception, e:
        module.fail_json(msg='Failed to connect to %s: %s' % (host, e))

    vm = server.get_vm_by_name(guest)
    power_status = 'UNKNOWN'
    changed = False

#    if module.params['media'] != None:
##         vm.set_extra_config({ 'bios.bootOrder': module.params['media'] })
#         vm.set_extra_config({ 'bios.bootDeviceClasses': 'allow:%s' % module.params['media'] })

         # FIXME: Implement connecting image using fd/cd
#         if module.params['image']:

    if state in ('boot_once', 'boot_always') or force:

        power_status = vm.get_status()

        if not force and power_status in ('POWERED ON', 'SUSPENDED', 'POWERING ON', 'RESETTING', 'BLOCKED ON MSG'):
            module.fail_json(msg='VMWare vSphere (%s) reports that the server \'%s\' is in state \'%s\' !' % (host, guest, power_status))

        if power_status in ('POWERED ON', 'POWERING ON', 'RESETTING'):
            vm.reset(sync_run=False)
            changed = True
        elif power_status in ('POWERED OFF', 'POWERING OFF'):
            vm.power_on(sync_run=False)
            changed = True
        else:
            module.fail_json(msg='VMWare vSphere (%s) reports that the server \'%s\' is in (unknown?) state \'%s\' !' % (host, guest, power_status))

    elif state in ('poweroff'):

        power_status = vm.get_status()

        if power_status not in ('POWERED OFF', 'POWERING OFF'):
            vm.power_off(sync_run=True)
            changed = True

    # FIXME: Make this smarter, check power_status until we are sure it has booted
#    if module.params['state'] in ('boot_once'):
#        time.sleep(10)
#        vm.set_extra_config({ 'bios.bootDeviceClasses': '' })
##        while time.sleep(1):
##            power_status = vm.get_status()
##            if power_status in ('POWERED ON',):
##                time.sleep(5000)
##                vm_set_extra_config({ 'bios.bootDeviceClasses': '')
##                break

    server.disconnect()
    module.exit_json(changed=changed, power=power_status)

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
if __name__ == '__main__':
    main()
