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
module: network_facts
short_description: Gather facts from DNS and a network inventory file
description:
  - This module gathers facts for a specific system using DNS and a separate
    network inventory YAML file. The host's IP address is matched with
    a given network range and the variables listed as part of this network
    range are automatically set for this hosts.
  - Using this module you can separate network-related settings per network
    (e.g. using different DNS servers, NTP servers, or even software
    distribution or provisioning servers based on the location of the network.
  - This module requires the netaddr python module.
version_added: "0.8"
options:
  host:
    description:
      - The host to use for gathering network-related facts.
    required: true
  inventory:
    description:
      - The inventory file consisting of network-related facts.
    default: /etc/ansible/network-inventory.yml
  full:
    description:
      - A boolean to decide whether a second DNS lookup is needed for the FQDN.
    default: no
  gateway:
    description:
      - The gateway strategy if no gateway was defined in the inventory.
      - Either 'first', 'last' or 'none'
      - This is useful if you have a standardized way of defining the gateway
        in your organization.
    default: last
examples:
    - description: Task to gather facts from a HP iLO interface only if the system is an HP server
      code: |
            local_action: network_facts host=$inventory_hostname inventory=network-inventory.yml
notes:
  - This module ought to be run from a system that can access the DNS
    interface directly, either by using C(local_action) or
    using C(delegate_to).
'''

import socket
import yaml
try:
    import netaddr
except ImportError:
    print "failed=True msg='netaddr python module unavailable'"
    sys.exit(1)


def main():

    module = AnsibleModule(
        argument_spec = dict(
            # Provided host can be IP address, hostname or FQDN
            host = dict(required=True, aliases=['name']),
            # FIXME: Allow to query a specific name server for DNS lookup
#            nameserver = dict(),
            full = dict(default='no', choices=BOOLEANS),
            gateway = dict(default='last', choices=['none', 'first', 'last']),
            inventory = dict(default='/etc/ansible/network-inventory.yml'),
        )
    )

    host = module.params.get('host')
    full = module.boolean(module.params.get('full'))
    gateway = module.params.get('gateway')
    inventory = module.params.get('inventory')

    inventory_file = None
    if inventory:
        inventory_file = os.path.expanduser(module.params.get('inventory'))

        if not os.path.exists(inventory_file):
            module.fail_json(msg="Inventory %s failed to transfer" % inventory_file)
        if not os.access(inventory_file, os.R_OK):
            module.fail_json(msg="Inventory %s not readable" % inventory_file)

    # Get IP address from DNS
    try:
        ipaddress = socket.gethostbyname(host)
    except Exception, e:
        module.fail_json(msg=str(e))

    ip = netaddr.IPAddress(ipaddress)
    facts = {
        'module_network': True,
        'network_ipaddress': str(ip),
        'network_ipaddress_hex': ('%08x' % ip).upper(),
    }

    # Do all DNS lookups if requested (so we get FQDN, aliases and more)
    if full:
        # Get FQDN from DNS
        try:
            fqdn = socket.getfqdn(host)
        except Exception, e:
            module.fail_json(msg=str(e))

        # FIXME: We can also return the reverse namelookup and aliases, if needed

        if ipaddress == fqdn == host:
            module.fail_json(msg='Name lookup for host %s failed' % host)

        facts['network_hostname'] = fqdn.split('.')[0]
        facts['network_fqdn'] = fqdn
        facts['network_domain'] = '.'.join(fqdn.split('.')[1:])

    # Most useful information comes from a separate inventory file
    # The inventory file _requires_ at least a cidr entry
    if inventory_file:
        networks = yaml.load(open(inventory_file))

        # Find the network
        for network in networks:

            net = netaddr.IPNetwork(network['cidr'])
            if ip not in net:
                continue

            # We have a match !
            facts['network_broadcast'] = str(net.broadcast)
            facts['network_netmask'] = str(net.netmask)
            facts['network_network'] = str(net.network)
            facts['network_bits'] = net.prefixlen

            for key in network:
                factname = 'network_'+key
                facts[factname] = network[key]

            # If no gateway is specified, take the last address from the range
            if 'gateway' not in network.keys():
                if gateway == 'first':
                    facts['network_gateway'] = str(netaddr.IPAddress(net.first + 1))
                elif gateway == 'last':
                    facts['network_gateway'] = str(netaddr.IPAddress(net.last - 1))
            break
        else:
            module.fail_json(msg='Network for host %s (%s) is missing from %s' % (host, str(ip), inventory_file))

    module.exit_json(ansible_facts=facts)

# this is magic, see lib/ansible/module_common.py
#<<INCLUDE_ANSIBLE_MODULE_COMMON>>
if __name__ == '__main__':
    main()
