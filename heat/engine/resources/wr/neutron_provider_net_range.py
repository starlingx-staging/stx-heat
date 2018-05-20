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


class ProviderNetRange(neutron.NeutronResource):
    """A resource for managing WR Neutron Provider Network Range.

    The WR Neutron Provider Network Range adds range capabilities to the
    WR Neutron Provider Network resource.
    """

    neutron_api_key = 'providernet_range'

    PROPERTIES = (
        PROVIDERNET_ID, NAME,
        MINIMUM, MAXIMUM,
        DESCRIPTION, SHARED,
        TENANT_ID, GROUP,
        TTL, PORT,
    ) = (
        'providernet_id', 'name',
        'minimum', 'maximum',
        'description', 'shared',
        'tenant_id', 'group',
        'ttl', 'port',
    )

    ATTRIBUTES = (
        NAME, DESCRIPTION, SHARED, MINIMUM, MAXIMUM,
    ) = (
        'name', 'description', 'shared', 'minimum', 'maximum'
    )

    properties_schema = {
        PROVIDERNET_ID: properties.Schema(
            properties.Schema.STRING,
            _('ID of the existing provider network.'),
            required=True,
        ),
        NAME: properties.Schema(
            properties.Schema.STRING,
            _('Name of the provider network range.'),
            required=True,
        ),
        MINIMUM: properties.Schema(
            properties.Schema.NUMBER,
            _('Minimum value for the range for this provider network range.'),
            required=True,
            update_allowed=True,
        ),
        MAXIMUM: properties.Schema(
            properties.Schema.NUMBER,
            _('Maximum value for the range for this provider network range.'),
            required=True,
            update_allowed=True,
        ),
        DESCRIPTION: properties.Schema(
            properties.Schema.STRING,
            _('Description for this provider network range.'),
            update_allowed=True,
        ),
        SHARED: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Whether provider network range is SHARED for all tenants.'),
            default=False,
        ),
        TENANT_ID: properties.Schema(
            properties.Schema.STRING,
            _('Tenant ID to assign to this range. '
              'Note: Only applied if range is not SHARED.'),
            constraints=[
                constraints.CustomConstraint('keystone.project')
            ],
        ),
        GROUP: properties.Schema(
            properties.Schema.STRING,
            _('Multicast IP addresses for VXLAN endpoints. '
              'Note: Only applied if provider net is VXLAN.'),
            update_allowed=True,
        ),
        TTL: properties.Schema(
            properties.Schema.NUMBER,
            _('Time-to-live value for VXLAN provider networks. '
              'Note: Only applied if provider net is VXLAN.'),
            update_allowed=True,
        ),
        PORT: properties.Schema(
            properties.Schema.NUMBER,
            _('Destination UDP port value to use for VXLAN provider networks. '
              'Note: Only valid values are 4789 or 8472. '
              'Note: Only applied if provider net is VXLAN. Default: 4789.'),
            update_allowed=True,
            constraints=[
                constraints.AllowedValues([4789, 8472]),
            ],
        ),
    }

    # Base class already has "show"
    attributes_schema = {
        NAME: attributes.Schema(
            _("The name of the provider network range."),
            type=attributes.Schema.STRING
        ),
        DESCRIPTION: attributes.Schema(
            _("The description of the provider network range."),
            type=attributes.Schema.STRING
        ),
        MAXIMUM: attributes.Schema(
            _('Maximum value for the range for this provider network range.'),
            type=attributes.Schema.NUMBER
        ),
        MINIMUM: attributes.Schema(
            _('Minimum value for the range for this provider network range.'),
            type=attributes.Schema.NUMBER
        ),
        SHARED: attributes.Schema(
            _('Whether this provider network range is shared or not.'),
            type=attributes.Schema.BOOLEAN
        ),
    }

    def validate(self):
        super(ProviderNetRange, self).validate()

    def prepare_properties(self, properties, name):
        props = super(ProviderNetRange, self).prepare_properties(properties,
                                                                 name)
        tenant = props.get(self.TENANT_ID)
        if tenant:
            # keystone project-list is the same as openstack tenant list"
            tenant_id = self.client_plugin('keystone').get_project_id(tenant)
            props[self.TENANT_ID] = tenant_id
        return props

    def handle_create(self):
        props = self.prepare_properties(
            self.properties,
            self.physical_resource_name())

        neutron_object = self.client().create_providernet_range(
            {self.neutron_api_key: props})[self.neutron_api_key]
        self.resource_id_set(neutron_object['id'])

    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        if prop_diff:
            self.prepare_update_properties(prop_diff)
            self.client().update_providernet_range(
                self.resource_id,
                {self.neutron_api_key: prop_diff})

    def _show_resource(self):
        return self.client().show_providernet_range(
            self.resource_id)[self.neutron_api_key]

    def handle_delete(self):
        if self.resource_id is None:
            return
        try:
            self.client().delete_providernet_range(self.resource_id)
        except neutron_exp.NeutronClientException as ex:
            self.client_plugin().ignore_not_found(ex)
        else:
            return True


def resource_mapping():
    return {
        'WR::Neutron::ProviderNetRange': ProviderNetRange,
    }
