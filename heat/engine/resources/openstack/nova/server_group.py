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
# Copyright (c) 2013-2015 Wind River Systems, Inc.
#

from heat.common.i18n import _
from heat.engine import constraints
from heat.engine import properties
from heat.engine import resource
from heat.engine import support

from heat.common import exception
from oslo_log import log as logging
from oslo_utils import excutils

LOG = logging.getLogger(__name__)

(GROUP_SIZE_METAKEY, BEST_EFFORT_METAKEY) = (
    'wrs-sg:group_size', 'wrs-sg:best_effort')


class ServerGroup(resource.Resource):
    """A resource for managing a Nova server group.

    Server groups allow you to make sure instances (VM/VPS) are on the same
    hypervisor host or on a different one.
    """

    support_status = support.SupportStatus(version='2014.2')

    default_client_name = 'nova'

    entity = 'server_groups'

    required_service_extension = 'os-server-groups'

    PROPERTIES = (
        NAME, POLICIES, GROUP_SIZE, BEST_EFFORT
    ) = (
        'name', 'policies', 'group_size', 'best_effort'
    )

    properties_schema = {
        NAME: properties.Schema(
            properties.Schema.STRING,
            _('Server Group name.')
        ),
        POLICIES: properties.Schema(
            properties.Schema.LIST,
            _('A list of string policies to apply. '
              'Defaults to anti-affinity.'),
            default=['anti-affinity'],
            constraints=[
                constraints.AllowedValues(["anti-affinity", "affinity",
                                           "soft-anti-affinity",
                                           "soft-affinity"])
            ],
            schema=properties.Schema(
                properties.Schema.STRING,
            )
        ),
        GROUP_SIZE: properties.Schema(
            properties.Schema.INTEGER,
            _('Maximum number of servers in the server group.'),
            update_allowed=True
        ),
        BEST_EFFORT: properties.Schema(
            properties.Schema.BOOLEAN,
            _('Whether the scheduler should still allow the server to '
              'be created even if it cannot satisfy the group policy.'),
            update_allowed=True
        ),
    }

    def handle_create(self):
        name = self.physical_resource_name()
        policies = self.properties[self.POLICIES]
        if 'soft-affinity' in policies or 'soft-anti-affinity' in policies:
            client = self.client(
                version=self.client_plugin().V2_15)
        else:
            client = self.client()

        group_size = self.properties.get(self.GROUP_SIZE)
        best_effort = self.properties.get(self.BEST_EFFORT)
        metadata = {}
        if group_size is not None:
            metadata[GROUP_SIZE_METAKEY] = str(group_size)
        if best_effort is not None:
            metadata[BEST_EFFORT_METAKEY] = str(best_effort).lower()

        project_id = self.context.tenant_id
        kwargs = {self.NAME: name,
                  'project_id': project_id,
                  self.POLICIES: policies,
                  'metadata': metadata}
        try:
            server_group = client.server_groups.create(**kwargs)
        except Exception:
            with excutils.save_and_reraise_exception():
                msg = _('Unable to create server group.')
                LOG.error(msg)
        self.resource_id_set(server_group.id)

    def physical_resource_name(self):
        name = self.properties[self.NAME]
        if name:
            return name
        return super(ServerGroup, self).physical_resource_name()

    def handle_update(self, json_snippet=None, tmpl_diff=None, prop_diff=None):
        # We don't currently handle server group metadata in the stack.
        # The stack "best_effort" and "group_size" properties actually map to
        # nova server group metadata.  Don't get confused. :)

        metadata = {}

        if self.BEST_EFFORT in prop_diff:
            best_effort = prop_diff[self.BEST_EFFORT]
            metadata[BEST_EFFORT_METAKEY] = str(best_effort).lower()

        if self.GROUP_SIZE in prop_diff:
            group_size = prop_diff[self.GROUP_SIZE]
            server_group = self.nova().server_groups.get(self.resource_id)
            if len(server_group.members) > group_size:
                raise exception.Invalid(
                    reason='Cannot update with a group size '
                           'smaller than the current number of '
                           'servers in the group')
            metadata[GROUP_SIZE_METAKEY] = str(group_size)

        self.nova().server_groups.set_metadata(self.resource_id, metadata)

    def validate(self):
        # Validate any of the provided params
        super(ServerGroup, self).validate()
        policies = self.properties.get(self.POLICIES)
        for policy in policies:
            if policy not in ('affinity', 'anti-affinity'):
                msg = _('Policy for server group %s must be "affinity" or '
                        '"anti-affinity"') % self.name
                raise exception.StackValidationFailed(message=msg)


def resource_mapping():
    return {'OS::Nova::ServerGroup': ServerGroup}
