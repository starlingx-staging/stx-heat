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


class NameEnhanceMixin(object):
    """Utility class to encapsulate WRS naming enhancements"""

    WRS_GROUP_INDEX_ENABLED = 'wrs-groupindex-mode'
    WRS_GROUP_INDEX = 'wrs-groupindex'

    def _enhance_name(self, name):
        metadata = self.metadata_get()
        # If wrs-groupindex-mode set in metadata
        # then  wrs-groupindex value appended to name
        # example:  Foo  ->  Foo1
        if metadata.get(self.WRS_GROUP_INDEX_ENABLED):
            gi = metadata.get(self.WRS_GROUP_INDEX, None)
            if gi is not None:
                return name + str(gi)
        return name
