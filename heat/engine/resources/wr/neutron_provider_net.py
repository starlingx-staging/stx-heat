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
# Copyright (c) 2013-2014 Wind River Systems, Inc.
#


from heat.common.i18n import _
from heat.engine import attributes
from heat.engine import constraints
from heat.engine import properties
from heat.engine.resources.openstack.neutron import neutron

from oslo_log import log as logging

import neutronclient.common.exceptions as neutron_exp

LOG = logging.getLogger(__name__)


class ProviderNet(neutron.NeutronResource):
    """A resource for WR Neutron Provider Network.

    The WR Neutron Provider Network is not the same as the
    regular Neutron Provider Network.
    """
    neutron_api_key = 'providernet'

    PROPERTIES = (
        NAME, TYPE, MTU, DESCRIPTION, VLAN_TRANSPARENT,
    ) = (
        'name', 'type', 'mtu', 'description', 'vlan_transparent',
    )

    ATTRIBUTES = (
        NAME, TYPE, MTU, STATUS, DESCRIPTION, VLAN_TRANSPARENT
    ) = (
        'name', 'type', 'mtu', 'status', 'description', 'vlan_transparent'
    )

    properties_schema = {
        DESCRIPTION: properties.Schema(
            properties.Schema.STRING,
            _('Description for the provider network.'),
            update_allowed=True,
        ),
        TYPE: properties.Schema(
            properties.Schema.STRING,
            _('The network type for the provider network.'),
            default='flat',
            constraints=[
                constraints.AllowedValues(['flat', 'vlan', 'vxlan']),
            ]
        ),
        MTU: properties.Schema(
            properties.Schema.NUMBER,
            _('Maximum transmit unit on the provider network. '
              'Note: default is 1500.'),
            update_allowed=True,
        ),
        VLAN_TRANSPARENT: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Allow VLAN tagged packets on tenant networks.'),
            default=False,
        ),
        NAME: properties.Schema(
            properties.Schema.STRING,
            _('Name of the provider network.'),
            required=True,
        ),
    }

    attributes_schema = {
        NAME: attributes.Schema(
            _("The name of the provider network."),
            type=attributes.Schema.STRING
        ),
        TYPE: attributes.Schema(
            _("The type of the provider network."),
            type=attributes.Schema.STRING
        ),
        MTU: attributes.Schema(
            _("MTU of the provider network."),
            type=attributes.Schema.NUMBER
        ),
        STATUS: attributes.Schema(
            _("The status of the provider network."),
            type=attributes.Schema.STRING
        ),
        DESCRIPTION: attributes.Schema(
            _("The description of the provider network."),
            type=attributes.Schema.STRING
        ),
        VLAN_TRANSPARENT: attributes.Schema(
            _("Flag if vlan transparent for the provider network."),
            type=attributes.Schema.BOOLEAN
        ),
    }

    def validate(self):
        super(ProviderNet, self).validate()

    def handle_create(self):
        props = self.prepare_properties(
            self.properties,
            self.physical_resource_name())
        neutron_object = self.client().create_providernet(
            {self.neutron_api_key: props})[self.neutron_api_key]
        self.resource_id_set(neutron_object['id'])

    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        if prop_diff:
            self.prepare_update_properties(prop_diff)
            self.client().update_providernet(self.resource_id,
                                             {self.neutron_api_key: prop_diff})

    def _show_resource(self):
        return self.client().show_providernet(
            self.resource_id)[self.neutron_api_key]

    def check_create_complete(self, *args):
        attributes = self._show_resource()
        return self.is_built(attributes)

    def check_update_complete(self, *args):
        attributes = self._show_resource()
        return self.is_built(attributes)

    def handle_delete(self):
        if self.resource_id is None:
            return
        try:
            self.client().delete_providernet(self.resource_id)
        except neutron_exp.NeutronClientException as ex:
            self.client_plugin().ignore_not_found(ex)
        else:
            return True


def resource_mapping():
    return {
        'WR::Neutron::ProviderNet': ProviderNet,
    }
