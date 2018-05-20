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
from heat.engine.resources.wr import neutron_provider_net_range as pnr
from heat.engine import rsrc_defn
from heat.engine import scheduler
from heat.tests import common
from heat.tests import utils


providernet_range_template = '''
heat_template_version: 2013-05-23
description: This template defines a provider net range
resources:
  my_providernet_range:
    type: WR::Neutron::ProviderNetRange
    properties:
         providernet_id: '1234'
         name : sample_providernet_range
         description: 'providernet_range description'
         minimum: 10
         maximum: 10
         shared: true
'''


def stub_fn(*args):
    pass


class NeutronProviderNetRangeTest(common.HeatTestCase):
    def setUp(self):
        super(NeutronProviderNetRangeTest, self).setUp()
        # If we are using a version of NeutronClient without WRS enhancements
        # we must update the client instance using setattr BEFORE we can stub
        try:
            print(neutronclient.Client.create_providernet_range)
        except Exception:
            # Assume that if create_portforwarding is missing all 4 are missing
            setattr(neutronclient.Client, 'create_providernet_range', stub_fn)
            setattr(neutronclient.Client, 'delete_providernet_range', stub_fn)
            setattr(neutronclient.Client, 'show_providernet_range', stub_fn)
            setattr(neutronclient.Client, 'update_providernet_range', stub_fn)
        self.m.StubOutWithMock(neutronclient.Client,
                               'create_providernet_range')
        self.m.StubOutWithMock(neutronclient.Client,
                               'delete_providernet_range')
        self.m.StubOutWithMock(neutronclient.Client,
                               'show_providernet_range')
        self.m.StubOutWithMock(neutronclient.Client,
                               'update_providernet_range')

    def create_providernet_range(self):
        neutronclient.Client.create_providernet_range({
            'providernet_range': {
                'providernet_id': '1234',
                'name': 'sample_providernet_range',
                'description': 'providernet_range description',
                'minimum': 10,
                'maximum': 10,
                'shared': True,
            }
        }).AndReturn({'providernet_range': {'id': '5678'}})

        snippet = template_format.parse(providernet_range_template)
        self.stack = utils.parse_stack(snippet)
        resource_defns = self.stack.t.resource_definitions(self.stack)
        return pnr.ProviderNetRange('providernet_range',
                                    resource_defns['my_providernet_range'],
                                    self.stack)

    def test_create(self):
        rsrc = self.create_providernet_range()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        self.assertEqual((rsrc.CREATE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()

    def test_create_failed(self):
        # This template is valid, but simulate a failure
        neutronclient.Client.create_providernet_range({
            'providernet_range': {
                'providernet_id': '1234',
                'name': 'sample_providernet_range',
                'description': 'providernet_range description',
                'minimum': 10,
                'maximum': 10,
                'shared': True,
            }
        }).AndRaise(exceptions.NeutronClientException())
        self.m.ReplayAll()

        snippet = template_format.parse(providernet_range_template)
        stack = utils.parse_stack(snippet)
        resource_defns = stack.t.resource_definitions(stack)
        rsrc = pnr.ProviderNetRange(
            'providernet_range', resource_defns['my_providernet_range'], stack)

        error = self.assertRaises(exception.ResourceFailure,
                                  scheduler.TaskRunner(rsrc.create))
        self.assertEqual(
            'NeutronClientException: resources.providernet_range:'
            ' An unknown exception occurred.',
            six.text_type(error))
        self.assertEqual((rsrc.CREATE, rsrc.FAILED), rsrc.state)
        self.m.VerifyAll()

    def test_delete(self):
        neutronclient.Client.delete_providernet_range('5678')
        neutronclient.Client.show_providernet_range('5678').AndRaise(
            exceptions.NeutronClientException(status_code=404))
        rsrc = self.create_providernet_range()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        scheduler.TaskRunner(rsrc.delete)()
        self.assertEqual((rsrc.DELETE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()

    def test_delete_already_gone(self):
        neutronclient.Client.delete_providernet_range('5678').AndRaise(
            exceptions.NeutronClientException(status_code=404))

        rsrc = self.create_providernet_range()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        scheduler.TaskRunner(rsrc.delete)()
        self.assertEqual((rsrc.DELETE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()

    def test_delete_failed(self):
        neutronclient.Client.delete_providernet_range('5678').AndRaise(
            exceptions.NeutronClientException(status_code=400))

        rsrc = self.create_providernet_range()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        error = self.assertRaises(exception.ResourceFailure,
                                  scheduler.TaskRunner(rsrc.delete))
        self.assertEqual(
            'NeutronClientException: resources.providernet_range:'
            ' An unknown exception occurred.',
            six.text_type(error))
        self.assertEqual((rsrc.DELETE, rsrc.FAILED), rsrc.state)
        self.m.VerifyAll()

    def test_attribute(self):
        rsrc = self.create_providernet_range()
        neutronclient.Client.show_providernet_range('5678').MultipleTimes(
        ).AndReturn({
            'providernet_range': {
                'providernet_id': '1234',
                'name': 'sample_providernet_range',
                'description': 'providernet_range description',
                'minimum': 10,
                'maximum': 10,
                'shared': True,
            }
        })
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        self.assertDictContainsSubset({'name': 'sample_providernet_range'},
                                      rsrc.FnGetAtt('show'))
        self.m.VerifyAll()

    def test_attribute_failed(self):
        rsrc = self.create_providernet_range()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        error = self.assertRaises(exception.InvalidTemplateAttribute,
                                  rsrc.FnGetAtt, 'FOO')
        self.assertEqual(
            'The Referenced Attribute (providernet_range FOO) is '
            'incorrect.', six.text_type(error))
        self.m.VerifyAll()

    # "tenant_id" is not an exposed attribute.
    def test_attribute_not_exposed(self):
        rsrc = self.create_providernet_range()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        error = self.assertRaises(exception.InvalidTemplateAttribute,
                                  rsrc.FnGetAtt, 'tenant_id')
        self.assertEqual(
            'The Referenced Attribute (providernet_range tenant_id) is '
            'incorrect.', six.text_type(error))
        self.m.VerifyAll()

    def mock_update_providernet_range(self,
                                      update_props,
                                      providernet_range_id='5678'):
        neutronclient.Client.update_providernet_range(
            providernet_range_id,
            {'providernet_range': update_props}).AndReturn(None)

    def test_update(self):
        rsrc = self.create_providernet_range()

        new_description = 'new description'
        update_props = {}
        update_props['description'] = new_description

        self.mock_update_providernet_range(update_props)
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
