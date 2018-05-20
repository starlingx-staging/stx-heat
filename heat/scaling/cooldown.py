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

from oslo_log import log as logging

from heat.common import exception
from heat.common.i18n import _
from heat.engine import resource
from oslo_config import cfg
from oslo_utils import timeutils
import six

LOG = logging.getLogger(__name__)


CONF = cfg.CONF


class CooldownMixin(object):
    """Utility class to encapsulate Cooldown related logic.

    This class is shared between AutoScalingGroup and ScalingPolicy.
    This logic includes both cooldown timestamp comparing and scaling in
    progress checking.
    """
    def _check_scaling_allowed(self):
        metadata = self.metadata_get()
        # WRS: If heat-engine is killed after setting scaling_in_progress
        # and before clearing the flag, the cooldown is blocked forever.
        # scaling_date provides a way of triggering a cleanup later
        if metadata.get('scaling_in_progress'):
            sd = metadata.get('scaling_date', None)
            if sd is None:
                LOG.info("Can not perform scaling action: resource %s "
                         "is already in scaling.", self.name)
                reason = _('due to scaling activity')
                raise resource.NoActionRequired(res_name=self.name,
                                                reason=reason)
            scale_max_time = CONF.cooldown.scaling_wait_time
            if not timeutils.is_older_than(sd, scale_max_time):
                LOG.info("Can not perform scaling action: resource %s "
                         "is already in scaling.", self.name)
                reason = _('due to scaling activity')
                raise resource.NoActionRequired(res_name=self.name,
                                                reason=reason)
        try:
            # Negative values don't make sense, so they are clamped to zero
            cooldown = max(0, self.properties[self.COOLDOWN])
        except TypeError:
            # If not specified, it will be None, same as cooldown == 0
            cooldown = 0

        if cooldown != 0:
            try:
                if 'cooldown' not in metadata:
                    # Note: this is for supporting old version cooldown logic
                    if metadata:
                        last_adjust = next(six.iterkeys(metadata))
                        self._cooldown_check(cooldown, last_adjust)
                else:
                    last_adjust = next(six.iterkeys(metadata['cooldown']))
                    self._cooldown_check(cooldown, last_adjust)
            except ValueError:
                # occurs when metadata has only {scaling_in_progress: False}
                pass

        # Assumes _finished_scaling is called
        # after the scaling operation completes
        metadata['scaling_in_progress'] = True
        metadata['scaling_date'] = timeutils.utcnow().isoformat()
        self.metadata_set(metadata)

    def _cooldown_check(self, cooldown, last_adjust):
        if not timeutils.is_older_than(last_adjust, cooldown):
            LOG.info("Can not perform scaling action: "
                     "resource %(name)s is in cooldown (%(cooldown)s).",
                     {'name': self.name,
                      'cooldown': cooldown})
            reason = _('due to cooldown, '
                       'cooldown %s') % cooldown
            raise resource.NoActionRequired(
                res_name=self.name, reason=reason)

    def _finished_scaling(self, cooldown_reason, size_changed=True):
        # If we wanted to implement the AutoScaling API like AWS does,
        # we could maintain event history here, but since we only need
        # the latest event for cooldown, just store that for now
        metadata = self.metadata_get()
        if size_changed:
            now = timeutils.utcnow().isoformat()
            metadata['cooldown'] = {now: cooldown_reason}
        metadata['scaling_in_progress'] = False
        try:
            self.metadata_set(metadata)
        except exception.NotFound:
            pass

    def handle_metadata_reset(self):
        metadata = self.metadata_get()
        if 'scaling_in_progress' in metadata:
            metadata['scaling_in_progress'] = False
            self.metadata_set(metadata)
