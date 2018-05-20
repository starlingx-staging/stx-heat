#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# Copyright (c) 2015 Wind River Systems, Inc.
#


from heat.common.i18n import _
from heat.engine import attributes
from heat.engine import constraints
from heat.engine import properties
from heat.engine.resources.openstack.neutron import neutron

from oslo_log import log as logging

import neutronclient.common.exceptions as neutron_exp

LOG = logging.getLogger(__name__)


class PortForwarding(neutron.NeutronResource):
    """A resource for managing Neutron virtual router port forwarding.

    The neutron API has been extended with support for virtual router port
    forwarding (i.e., DNAT). This resource adds port forwarding rules.
    """
    neutron_api_key = 'portforwarding'

    PROPERTIES = (
        ROUTER_ID, INSIDE_ADDR, INSIDE_PORT,
        OUTSIDE_PORT, PROTOCOL, DESCRIPTION,
    ) = (
        'router_id',
        'inside_addr', 'inside_port', 'outside_port',
        'protocol', 'description',
    )

    ATTRIBUTES = (
        SHOW, ROUTER_ID, PORT_ID, INSIDE_ADDR, INSIDE_PORT,
        OUTSIDE_PORT, PROTOCOL, DESCRIPTION,
    ) = (
        'show', 'router_id', 'port_id',
        'inside_addr', 'inside_port', 'outside_port',
        'protocol', 'description',
    )

    properties_schema = {
        ROUTER_ID: properties.Schema(
            properties.Schema.STRING,
            _('The name or uuid of the virtual router.'),
            required=True,
            constraints=[
                constraints.CustomConstraint('neutron.router')
            ],
        ),
        INSIDE_ADDR: properties.Schema(
            properties.Schema.STRING,
            _('The private IPv4 address to be the destination of the '
              'forwarding rule.'),
            required=True,
            update_allowed=True,
            constraints=[
                constraints.AllowedPattern(
                    '^[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}$',
                    description='IPv4 Address'),
            ]
        ),
        INSIDE_PORT: properties.Schema(
            properties.Schema.NUMBER,
            _('The private layer4 protocol port number to be the destination '
              'of the forwarding rule.'),
            required=True,
            constraints=[
                constraints.Range(min=0, max=65535),
            ],
            update_allowed=True
        ),
        OUTSIDE_PORT: properties.Schema(
            properties.Schema.NUMBER,
            _('The public layer4 protocol port number.'),
            required=True,
            constraints=[
                constraints.Range(min=0, max=65535),
            ],
            update_allowed=True
        ),
        PROTOCOL: properties.Schema(
            properties.Schema.STRING,
            _('The layer4 protocol type.'),
            required=True,
            constraints=[
                constraints.AllowedValues(['tcp', 'udp', 'udp-lite',
                                           'sctp', 'dccp']),
            ],
            update_allowed=True
        ),
        DESCRIPTION: properties.Schema(
            properties.Schema.STRING,
            _('User defined descriptive text.'),
            update_allowed=True
        ),
    }

    attributes_schema = {
        ROUTER_ID: attributes.Schema(
            _("The parent virtual router."),
            type=attributes.Schema.STRING
        ),
        PORT_ID: attributes.Schema(
            _("The virtual port associated to the private IPv4 address."),
            type=attributes.Schema.STRING
        ),
        INSIDE_ADDR: attributes.Schema(
            _("The private IPv4 address."),
            type=attributes.Schema.STRING
        ),
        INSIDE_PORT: attributes.Schema(
            _("The private layer4 protocol port number."),
            type=attributes.Schema.INTEGER
        ),
        OUTSIDE_PORT: attributes.Schema(
            _("The public layer4 protocol port number."),
            type=attributes.Schema.INTEGER
        ),
        PROTOCOL: attributes.Schema(
            _("The layer4 protocol name."),
            type=attributes.Schema.STRING
        ),
        DESCRIPTION: attributes.Schema(
            _("The user defined descriptive text."),
            type=attributes.Schema.STRING
        )
    }

    def validate(self):
        super(PortForwarding, self).validate()

    def handle_create(self):
        props = self.prepare_properties(
            self.properties,
            self.physical_resource_name())
        neutron_object = self.client().create_portforwarding(
            {self.neutron_api_key: props})[self.neutron_api_key]
        self.resource_id_set(neutron_object['id'])

    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        if prop_diff:
            self.prepare_update_properties(prop_diff)
            # Do special case handling based on props.
            # No special cases at this time.
            LOG.debug('updating portforwarding with %s' % prop_diff)
            self.client().update_portforwarding(
                self.resource_id, {self.neutron_api_key: prop_diff})

    def _show_resource(self):
        return self.client().show_portforwarding(
            self.resource_id)[self.neutron_api_key]

    def check_create_complete(self, *args):
        attributes = self._show_resource()
        return bool('id' in attributes)

    def check_update_complete(self, *args):
        attributes = self._show_resource()
        return bool('id' in attributes)

    def handle_delete(self):
        if self.resource_id is None:
            return
        try:
            self.client().delete_portforwarding(self.resource_id)
        except neutron_exp.NeutronClientException as ex:
            self.client_plugin().ignore_not_found(ex)
        else:
            return True


def resource_mapping():
    return {
        'WR::Neutron::PortForwarding': PortForwarding,
    }
