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

from heat.common import template_format
from heat.engine.resources.openstack.glance import image as gi
from heat.engine import stack
from heat.engine import template
from heat.tests import common
from heat.tests import utils


# WRS  Glance Image enhancements
# Location support for local files
# new  cache_raw property

image_file_template = '''
heat_template_version: 2013-05-23
description: This template to define a glance image.
resources:
  my_image:
    type: OS::Glance::Image
    properties:
      name: cirros_image
      id: 41f0e60c-ebb4-4375-a2b4-845ae8b9c995
      disk_format: qcow2
      container_format: bare
      is_public: True
      min_disk: 10
      min_ram: 512
      protected: False
      location: file:///some_folder/some_file.img
      cache_raw: False
'''


class GlanceFileImageTest(common.HeatTestCase):
    def setUp(self):
        super(GlanceFileImageTest, self).setUp()

        utils.setup_dummy_db()
        self.ctx = utils.dummy_context()

        tpl = template_format.parse(image_file_template)
        self.stack = stack.Stack(
            self.ctx, 'glance_image_test_stack_wr',
            template.Template(tpl)
        )

        self.my_image = self.stack['my_image']
        glance = mock.MagicMock()
        self.glanceclient = mock.MagicMock()
        self.my_image.client = glance
        glance.return_value = self.glanceclient
        self.images = self.glanceclient.images

    @mock.patch.object(gi.GlanceImage, '_load_local_file')
    def test_image_handle_create(self, mock_load):
        mock_load.return_value = None
        value = mock.MagicMock()
        image_id = '41f0e60c-ebb4-4375-a2b4-845ae8b9c995'
        value.id = image_id
        self.images.create.return_value = value
        self.my_image.handle_create()
        self.assertEqual(image_id, self.my_image.resource_id)

    def test_invalid_image_handle_create(self):
        exc = self.assertRaises(IOError, self.my_image.handle_create)
        self.assertIn("No such file", six.text_type(exc))
