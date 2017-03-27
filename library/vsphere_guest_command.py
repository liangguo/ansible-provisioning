#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2013 Merlijn Hofstra <mhofstra *AT* gmail.com>
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
author: Merlijn Hofstra
module: vsphere_guest_command
short_description: Execute a command on a VMware vSphere guest
description:
  - This module executes a command for a specific guest on VMWare vSphere.
    This can be used to run commands on a machine that is not SSH accessible.
  - This module requires the pysphere python module.
  - This module requires logins to the guest OS
version_added: "1.2"
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
  guestlogin:
    description:
      - The login name for the guest OS.
    required: true
  guestpassword:
    description:
      - The password for the guest OS.
    required: true
  command:
    description:
      - The command to execute in the guest OS.
    required: true
  args:
    description:
      - Arguments for the command.
    required: false
  env:
    description:
      - Environment variables passed to the command.
    required: false
  cwd:
    description:
      - Working directory for the command.
    required: false
examples:
  - description: Bring up the eth0 interface
    code: |
      - local_action: vsphere_guest_command host=$esxserver login=$esxlogin password=$esxpassword guest=$guestname guestlogin=root guestpassword=secret command=/sbin/ifconfig args="eth0 up"
        only_if: "'$cmdb_hwmodel'.startswith('VMWare ')
notes:
  - This module ought to be run from a system that can access vSphere directly.
    Either by using local_action, or using delegate_to.
  - You will not recieve output of the command executed, the command is forked in the background and only a PID is returned
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
            guestlogin = dict(required=True),
            guestpassword = dict(required=True),
            guest = dict(required=True, aliases=['name']),
            command = dict(required=True),
            args = dict(required=False),
            env = dict(required=False),
            cwd = dict(required=False)
        )
    )

    host = module.params.get('host')
    login = module.params.get('login')
    password = module.params.get('password')
    guest = module.params.get('guest')
    guestlogin = module.params.get('guestlogin')
    guestpassword = module.params.get('guestpassword')
    command = module.params.get('command')
    args = module.params.get('args')
    env = module.params.get('env')
    cwd = module.params.get('cwd')

    server = pysphere.VIServer()
    try:
        server.connect(host, login, password)
    except Exception, e:
        module.fail_json(msg='Failed to connect to %s: %s' % (host, e))

    try:
        vm = server.get_vm_by_name(guest)
    except pysphere.resources.vi_exception.VIException, e:
        module.fail_json(msg=e.message)
        
    try:
        vm.login_in_guest(guestlogin, guestpassword)
    except pysphere.resources.vi_exception.VIException, e:
        module.fail_json(msg=e.message)

    try:
        pid = vm.start_process(command, args.split(" "), env, cwd)
    except pysphere.resources.vi_exception.VIException, e:
        module.fail_json(msg=e.message)

    server.disconnect()
    module.exit_json(changed=True, pid=pid)

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
if __name__ == '__main__':
    main()
