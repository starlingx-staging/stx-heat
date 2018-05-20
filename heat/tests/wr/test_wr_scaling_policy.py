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
#  Copyright (c) 2015 Wind River Systems, Inc.
#

import mock
import six

from oslo_config import cfg

from heat.common import exception
from heat.common import template_format
from heat.engine.clients.os import nova
from heat.engine import resource
from heat.engine import scheduler
from heat.tests.common import HeatTestCase
from heat.tests import utils

from heat.engine.resources.wr import wr_scaling_policy as sp

as_template = '''
{
    'heat_template_version': '2013-05-23',
    'resources': {
        'scale_up': {
            'type': 'OS::WR::ScalingPolicy',
            'properties': {
                'ServerName': '5678',
                'ScalingResource': 'cpu',
                'ScalingDirection': 'up',
                'Cooldown': '60',
            }
        }
    }
}
'''


class ScalingPolicyTest(HeatTestCase):
    def setUp(self):
        super(ScalingPolicyTest, self).setUp()
        cfg.CONF.set_default('heat_waitcondition_server_url',
                             'http://server.test:8000/v1/waitcondition')
        self.stub_keystoneclient()
        self.ctx = utils.dummy_context()

        # For unit testing purpose. Register resource provider
        # explicitly.
        resource._register_class("OS::WR::ScalingPolicy", sp.ScalingPolicy)

    def _stub_nova_server_get(self, not_found=False):
        mock_server = mock.MagicMock()
        mock_server.image = {'id': 'dd619705-468a-4f7d-8a06-b84794b3561a'}
        if not_found:
            self.patchobject(nova.NovaClientPlugin, 'get_server',
                             side_effect=exception.EntityNotFound(
                                 entity='Server',
                                 name='5678'))
        else:
            self.patchobject(nova.NovaClientPlugin, 'get_server',
                             return_value=mock_server)

    def create_scaling_policy(self, t, stack, resource_name):
        rsrc = stack[resource_name]
        self.assertIsNone(rsrc.validate())
        scheduler.TaskRunner(rsrc.create)()
        self.assertEqual((rsrc.CREATE, rsrc.COMPLETE), rsrc.state)
        return rsrc

    def test_resource_mapping(self):
        mapping = sp.resource_mapping()
        self.assertEqual(1, len(mapping))
        self.assertEqual(sp.ScalingPolicy, mapping['OS::WR::ScalingPolicy'])

    def test_scaling_policy_constraint_validation(self):
        self._stub_nova_server_get(not_found=True)
        t = template_format.parse(as_template)
        stack = utils.parse_stack(t)
        exc = self.assertRaises(exception.StackValidationFailed,
                                stack.validate)
        self.assertIn("The Server (5678) could not be found.",
                      six.text_type(exc))
        self.m.ReplayAll()
        self.m.VerifyAll()

    def test_scaling_policy_creation(self):
        t = template_format.parse(as_template)
        stack = utils.parse_stack(t)
        self._stub_nova_server_get()
        self.m.ReplayAll()
        self.create_scaling_policy(t, stack, 'scale_up')
        self.m.VerifyAll()

    def test_scaling_policy_signal(self):
        t = template_format.parse(as_template)
        stack = utils.parse_stack(t)
        self._stub_nova_server_get()
        self.m.ReplayAll()
        up_policy = self.create_scaling_policy(t, stack, 'scale_up')
        up_policy.handle_signal()
        self.m.VerifyAll()
