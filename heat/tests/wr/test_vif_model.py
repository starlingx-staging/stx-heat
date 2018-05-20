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

import mock
import six

from heat.common import exception
from heat.common import template_format
from heat.engine.clients.os import glance
from heat.engine.clients.os import neutron
from heat.engine.clients.os import nova
from heat.engine import stack
from heat.engine import template
from heat.tests import common
from heat.tests import utils

test_template_vif_model = '''
heat_template_version: 2013-05-23
resources:
    vif_server:
        type: OS::Nova::Server
        properties:
            image: wrl6
            flavor: 1234
            networks:
            - { network: 12345, vif-model: virtio }
'''

test_template_bad_vif_model = '''
heat_template_version: 2013-05-23
resources:
    vif_server:
        type: OS::Nova::Server
        properties:
            image: wrl6
            flavor: 1234
            networks:
            - { network: 12345, vif-model: broken }
'''


# The purpose of these unit tests is to test validation
# We do not test nova server creation itself
class VifModelTest(common.HeatTestCase):

    def setUp(self):
        super(VifModelTest, self).setUp()
        self.tenant_id = 'test_tenant'
        self.novaclient = mock.Mock()
        self.m.StubOutWithMock(nova.NovaClientPlugin, '_create')
        self.m.StubOutWithMock(self.novaclient.servers, 'get')
        self.patchobject(nova.NovaClientPlugin, 'get_server',
                         return_value=mock.MagicMock())
        self.mock_image = mock.Mock(min_ram=128, min_disk=1, status='active')
        self.patchobject(glance.GlanceClientPlugin, 'get_image',
                         return_value=self.mock_image)
        self.mock_flavor = mock.Mock(ram=128, disk=1)
        self.patchobject(nova.NovaClientPlugin, 'get_flavor',
                         return_value=self.mock_flavor)
        self.patchobject(neutron.NeutronClientPlugin,
                         'find_resourceid_by_name_or_id')

    def test_vif_model_valid(self):
        tpl = template_format.parse(test_template_vif_model)
        ctx = utils.dummy_context(tenant_id=self.tenant_id)
        stk = stack.Stack(ctx, 'test_stack', template.Template(tpl))
        stk.validate()

    def test_vif_model_invalid(self):
        tpl = template_format.parse(test_template_bad_vif_model)
        ctx = utils.dummy_context(tenant_id=self.tenant_id)
        stk = stack.Stack(ctx, 'test_stack', template.Template(tpl))
        exc = self.assertRaises(exception.StackValidationFailed,
                                stk.validate)
        self.assertIn("is not a supported vif-model", six.text_type(exc))
