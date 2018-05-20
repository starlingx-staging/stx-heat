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

import copy

from neutronclient.common import exceptions
from neutronclient.v2_0 import client as neutronclient
import six

from heat.common import exception
from heat.common import template_format
from heat.engine.resources.wr import neutron_provider_net as pnr
from heat.engine import rsrc_defn
from heat.engine import scheduler
from heat.tests import common
from heat.tests import utils


providernet_template = '''
heat_template_version: 2015-04-30
description: This template defines a provider net
resources:
  my_providernet:
    type: WR::Neutron::ProviderNet
    properties:
         name : sample_providernet
         description: 'providernet description'
         type: vlan
         mtu: 1500
'''

pr_dict_id = "9649c220-874e-443c-a2ab-d6ac7ccf7b35"
pr_dict_done = {
    "providernet": {
        "status": "DOWN",
        "description": "providernet description",
        "mtu": 1500,
        "ranges": [],
        "type": "vlan",
        "id": pr_dict_id,
        "name": "sample_providernet",
        "vlan_transparent": False,
    }
}

pr_dict_build = copy.deepcopy(pr_dict_done)
pr_dict_build['providernet']['status'] = "BUILD"


def stub_fn(*args):
    pass


class NeutronProviderNetTest(common.HeatTestCase):
    def setUp(self):
        super(NeutronProviderNetTest, self).setUp()
        # If we are using a version of NeutronClient without WRS enhancements
        # we must update the client instance using setattr BEFORE we can stub
        try:
            print(neutronclient.Client.create_providernet)
        except Exception:
            # Assume that if create_portforwarding is missing all 4 are missing
            setattr(neutronclient.Client, 'create_providernet', stub_fn)
            setattr(neutronclient.Client, 'delete_providernet', stub_fn)
            setattr(neutronclient.Client, 'show_providernet', stub_fn)
            setattr(neutronclient.Client, 'update_providernet', stub_fn)

        self.m.StubOutWithMock(neutronclient.Client,
                               'create_providernet')
        self.m.StubOutWithMock(neutronclient.Client,
                               'delete_providernet')
        self.m.StubOutWithMock(neutronclient.Client,
                               'show_providernet')
        self.m.StubOutWithMock(neutronclient.Client,
                               'update_providernet')

    def create_providernet(self):
        neutronclient.Client.create_providernet({
            'providernet': {
                'name': 'sample_providernet',
                'description': 'providernet description',
                'type': 'vlan',
                'mtu': 1500,
                'vlan_transparent': False,
            }
        }).AndReturn(pr_dict_done)

        neutronclient.Client.show_providernet(
            pr_dict_id
        ).AndReturn(pr_dict_build)

        neutronclient.Client.show_providernet(
            pr_dict_id
        ).AndReturn(pr_dict_done)

        snippet = template_format.parse(providernet_template)
        self.stack = utils.parse_stack(snippet)
        resource_defns = self.stack.t.resource_definitions(self.stack)
        return pnr.ProviderNet('providernet',
                               resource_defns['my_providernet'],
                               self.stack)

    def test_create(self):
        rsrc = self.create_providernet()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        self.assertEqual((rsrc.CREATE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()

    def test_create_failed(self):
        # This template is valid, but simulate a failure
        neutronclient.Client.create_providernet({
            'providernet': {
                'name': 'sample_providernet',
                'description': 'providernet description',
                'type': 'vlan',
                'mtu': 1500,
                'vlan_transparent': False,
            }
        }).AndRaise(exceptions.NeutronClientException())
        self.m.ReplayAll()

        snippet = template_format.parse(providernet_template)
        stack = utils.parse_stack(snippet)
        resource_defns = stack.t.resource_definitions(stack)
        rsrc = pnr.ProviderNet(
            'providernet', resource_defns['my_providernet'], stack)

        error = self.assertRaises(exception.ResourceFailure,
                                  scheduler.TaskRunner(rsrc.create))
        self.assertEqual(
            'NeutronClientException: resources.providernet:'
            ' An unknown exception occurred.',
            six.text_type(error))
        self.assertEqual((rsrc.CREATE, rsrc.FAILED), rsrc.state)
        self.m.VerifyAll()

    def test_delete(self):
        rsrc = self.create_providernet()
        neutronclient.Client.delete_providernet(pr_dict_id)
        neutronclient.Client.show_providernet(pr_dict_id).AndRaise(
            exceptions.NeutronClientException(status_code=404))
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        scheduler.TaskRunner(rsrc.delete)()
        self.assertEqual((rsrc.DELETE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()

    def test_delete_already_gone(self):
        neutronclient.Client.delete_providernet(pr_dict_id).AndRaise(
            exceptions.NeutronClientException(status_code=404))

        rsrc = self.create_providernet()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        scheduler.TaskRunner(rsrc.delete)()
        self.assertEqual((rsrc.DELETE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()

    def test_delete_failed(self):
        neutronclient.Client.delete_providernet(pr_dict_id).AndRaise(
            exceptions.NeutronClientException(status_code=400))

        rsrc = self.create_providernet()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        error = self.assertRaises(exception.ResourceFailure,
                                  scheduler.TaskRunner(rsrc.delete))
        self.assertEqual(
            'NeutronClientException: resources.providernet:'
            ' An unknown exception occurred.',
            six.text_type(error))
        self.assertEqual((rsrc.DELETE, rsrc.FAILED), rsrc.state)
        self.m.VerifyAll()

    def test_attribute(self):
        rsrc = self.create_providernet()
        neutronclient.Client.show_providernet(pr_dict_id).MultipleTimes(
        ).AndReturn({
            'providernet': {
                'providernet_id': '1234',
                'name': 'sample_providernet',
                'description': 'providernet description',
                'minimum': 10,
                'maximum': 10,
                'shared': True,
            }
        })
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        self.assertDictContainsSubset({'name': 'sample_providernet'},
                                      rsrc.FnGetAtt('show'))
        self.m.VerifyAll()

    def test_attribute_failed(self):
        rsrc = self.create_providernet()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        error = self.assertRaises(exception.InvalidTemplateAttribute,
                                  rsrc.FnGetAtt, 'FOO')
        self.assertEqual(
            'The Referenced Attribute (providernet FOO) is '
            'incorrect.', six.text_type(error))
        self.m.VerifyAll()

    # "tenant_id" is not an exposed attribute
    def test_attribute_not_exposed(self):
        rsrc = self.create_providernet()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        error = self.assertRaises(exception.InvalidTemplateAttribute,
                                  rsrc.FnGetAtt, 'tenant_id')
        self.assertEqual(
            'The Referenced Attribute (providernet tenant_id) is '
            'incorrect.', six.text_type(error))
        self.m.VerifyAll()

    def mock_update_providernet(self,
                                update_props,
                                providernet_id=pr_dict_id):
        neutronclient.Client.update_providernet(
            providernet_id,
            {'providernet': update_props}).AndReturn(None)

    def test_update(self):
        rsrc = self.create_providernet()

        new_description = 'new description'
        # We MUST pass the entire structure to an update
        # We only pass the values that are editable
        update_props = {}
        update_props['description'] = new_description

        self.mock_update_providernet(update_props)
        pr_dict_changed = copy.deepcopy(pr_dict_done)
        pr_dict_changed['providernet']['description'] = new_description
        neutronclient.Client.show_providernet(
            pr_dict_id
        ).AndReturn(pr_dict_changed)
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        self.assertEqual((rsrc.CREATE, rsrc.COMPLETE), rsrc.state)

        # Do an update
        props = copy.deepcopy(rsrc.properties.data)
        props['description'] = new_description
        snippet = rsrc_defn.ResourceDefinition(rsrc.name, rsrc.type(), props)
        scheduler.TaskRunner(rsrc.update, snippet)()

        self.assertEqual((rsrc.UPDATE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()
