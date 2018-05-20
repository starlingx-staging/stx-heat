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

import copy
import mock
import six

from neutronclient.common import exceptions
from neutronclient.v2_0 import client as neutronclient

from heat.common import exception
from heat.common import template_format
from heat.engine.clients.os.neutron import neutron_constraints
from heat.engine.resources.wr import neutron_port_forwarding as npf
from heat.engine import scheduler
from heat.tests import common
from heat.tests import utils


port_forwarding_template = '''
heat_template_version: 2015-04-30
description: This template defines a virtual router port forwarding rule
resources:
  my_rule:
    type: WR::Neutron::PortForwarding
    properties:
         router_id: 9649c220-874e-443c-a2ab-d6ac7ccf7b3
         inside_addr: 192.168.1.25
         inside_port: 80
         outside_port: 8080
         protocol: tcp
         description: 'port forwarding rule description'
'''

tenant_id = "dd1c1ebd-d104-4988-be3b-3b1e1d59bfae"
router_id = "9649c220-874e-443c-a2ab-d6ac7ccf7b3"
port_id = "a4a28ac1-73a3-4793-b139-7cf4449f392e"
pfr_dict_id = "2f096d58-f0c4-478a-9a49-0196fe1b0871"
pfr_dict = {
    "id": pfr_dict_id,
    "port_id": port_id,
    "router_id": router_id,
    "tenant_id": tenant_id,
    "inside_addr": "192.168.1.25",
    "inside_port": 80,
    "outside_port": 8080,
    "protocol": "tcp",
    "description": "port forwarding rule description",
}

pfr_dict_done = {
    "portforwarding": pfr_dict
}


def stub_fn(*args):
    pass


class NeutronPortForwardingTest(common.HeatTestCase):

    def setUp(self):
        super(NeutronPortForwardingTest, self).setUp()
        self.m.StubOutWithMock(neutron_constraints.RouterConstraint,
                               'validate_with_client')

        # If we are using a version of NeutronClient without portforwarding
        # we must update the client instance using setattr BEFORE we can stub
        try:
            print(neutronclient.Client.create_portforwarding)
        except Exception:
            # Assume that if create_portforwarding is missing all 4 are missing
            setattr(neutronclient.Client, 'create_portforwarding', stub_fn)
            setattr(neutronclient.Client, 'delete_portforwarding', stub_fn)
            setattr(neutronclient.Client, 'show_portforwarding', stub_fn)
            setattr(neutronclient.Client, 'update_portforwarding', stub_fn)

        self.m.StubOutWithMock(neutronclient.Client,
                               'create_portforwarding')
        self.m.StubOutWithMock(neutronclient.Client,
                               'delete_portforwarding')
        self.m.StubOutWithMock(neutronclient.Client,
                               'show_portforwarding')
        self.m.StubOutWithMock(neutronclient.Client,
                               'update_portforwarding')

    def create_portforwarding(self):
        neutron_constraints.RouterConstraint.validate_with_client(
            mock.ANY, pfr_dict['router_id']
        ).AndReturn(None)

        neutronclient.Client.create_portforwarding({
            'portforwarding': {
                'router_id': pfr_dict['router_id'],
                'inside_addr': pfr_dict['inside_addr'],
                'inside_port': pfr_dict['inside_port'],
                'outside_port': pfr_dict['outside_port'],
                'protocol': pfr_dict['protocol'],
                'description': pfr_dict['description'],
            }
        }).AndReturn(pfr_dict_done)

        neutronclient.Client.show_portforwarding(
            pfr_dict_id
        ).AndReturn(pfr_dict_done)

        snippet = template_format.parse(port_forwarding_template)
        self.stack = utils.parse_stack(snippet)
        resource_defns = self.stack.t.resource_definitions(self.stack)
        return npf.PortForwarding('portforwarding',
                                  resource_defns['my_rule'],
                                  self.stack)

    def test_create(self):
        rsrc = self.create_portforwarding()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        self.assertEqual((rsrc.CREATE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()

    def test_create_failed(self):
        neutron_constraints.RouterConstraint.validate_with_client(
            mock.ANY, pfr_dict['router_id']
        ).AndReturn(None)

        # This template is valid, but simulate a failure
        neutronclient.Client.create_portforwarding({
            'portforwarding': {
                'router_id': pfr_dict['router_id'],
                'inside_addr': pfr_dict['inside_addr'],
                'inside_port': pfr_dict['inside_port'],
                'outside_port': pfr_dict['outside_port'],
                'protocol': pfr_dict['protocol'],
                'description': pfr_dict['description'],
            }
        }).AndRaise(exceptions.NeutronClientException())
        self.m.ReplayAll()

        snippet = template_format.parse(port_forwarding_template)
        stack = utils.parse_stack(snippet)
        resource_defns = stack.t.resource_definitions(stack)
        rsrc = npf.PortForwarding(
            'portforwarding', resource_defns['my_rule'], stack)

        error = self.assertRaises(exception.ResourceFailure,
                                  scheduler.TaskRunner(rsrc.create))

        self.assertEqual(
            'NeutronClientException: resources.portforwarding:' +
            ' An unknown exception occurred.',
            six.text_type(error))
        self.assertEqual((rsrc.CREATE, rsrc.FAILED), rsrc.state)
        self.m.VerifyAll()

    def test_delete(self):
        rsrc = self.create_portforwarding()
        neutronclient.Client.delete_portforwarding(pfr_dict_id)
        neutronclient.Client.show_portforwarding(pfr_dict_id).AndRaise(
            exceptions.NeutronClientException(status_code=404))
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        scheduler.TaskRunner(rsrc.delete)()
        self.assertEqual((rsrc.DELETE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()

    def test_delete_already_gone(self):
        neutronclient.Client.delete_portforwarding(pfr_dict_id).AndRaise(
            exceptions.NeutronClientException(status_code=404))

        rsrc = self.create_portforwarding()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        scheduler.TaskRunner(rsrc.delete)()
        self.assertEqual((rsrc.DELETE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()

    def test_delete_failed(self):
        neutronclient.Client.delete_portforwarding(pfr_dict_id).AndRaise(
            exceptions.NeutronClientException(status_code=400))

        rsrc = self.create_portforwarding()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        error = self.assertRaises(exception.ResourceFailure,
                                  scheduler.TaskRunner(rsrc.delete))
        self.assertEqual(
            'NeutronClientException: resources.portforwarding:' +
            ' An unknown exception occurred.',
            six.text_type(error))
        self.assertEqual((rsrc.DELETE, rsrc.FAILED), rsrc.state)
        self.m.VerifyAll()

    def test_attribute(self):
        rsrc = self.create_portforwarding()
        neutronclient.Client.show_portforwarding(pfr_dict_id).MultipleTimes(
        ).AndReturn(pfr_dict_done)
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        self.assertDictContainsSubset({'port_id': port_id},
                                      rsrc.FnGetAtt('show'))
        self.m.VerifyAll()

    def test_attribute_failed(self):
        rsrc = self.create_portforwarding()
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        error = self.assertRaises(exception.InvalidTemplateAttribute,
                                  rsrc.FnGetAtt, 'FOO')
        self.assertEqual(
            'The Referenced Attribute (portforwarding FOO) is '
            'incorrect.', six.text_type(error))
        self.m.VerifyAll()

    def mock_update_portforwarding(self,
                                   update_props,
                                   portforwarding_id=pfr_dict_id):
        neutron_constraints.RouterConstraint.validate_with_client(
            mock.ANY, pfr_dict['router_id']
        ).AndReturn(None)

        neutronclient.Client.update_portforwarding(
            portforwarding_id,
            {'portforwarding': update_props}).AndReturn(None)

    def test_update(self):
        rsrc = self.create_portforwarding()

        new_description = 'new description'
        update_props = {'description': new_description}
        self.mock_update_portforwarding(update_props)
        pfr_dict_changed = copy.deepcopy(pfr_dict_done)
        pfr_dict_changed['portforwarding']['description'] = new_description
        neutronclient.Client.show_portforwarding(
            pfr_dict_id
        ).AndReturn(pfr_dict_changed)
        self.m.ReplayAll()
        scheduler.TaskRunner(rsrc.create)()
        self.assertEqual((rsrc.CREATE, rsrc.COMPLETE), rsrc.state)

        # Do an update
        props = rsrc.t._properties.copy()
        props['description'] = new_description
        update_template = rsrc.t.freeze(properties=props)
        scheduler.TaskRunner(rsrc.update, update_template)()

        self.assertEqual((rsrc.UPDATE, rsrc.COMPLETE), rsrc.state)
        self.m.VerifyAll()
