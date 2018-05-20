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

from oslo_log import log as logging
import six

from heat.common.i18n import _
from heat.engine import attributes
from heat.engine import constraints
from heat.engine import properties
from heat.engine import resource
from heat.engine.resources import signal_responder
from heat.scaling import cooldown

LOG = logging.getLogger(__name__)


class ScalingPolicy(signal_responder.SignalResponder,
                    cooldown.CooldownMixin):
    """A Resource for scaling Guest VCPUs.

    This enables HEAT framework to dynamically resize (in terms of number of
    guest vcpus) a VM when policy criteria described in the template is met.
    """

    PROPERTIES = (
        SERVER_NAME, SCALING_RESOURCE, SCALING_DIRECTION,
        COOLDOWN,
    ) = (
        'ServerName', 'ScalingResource', 'ScalingDirection', 'Cooldown',
    )

    SCALE_UP, SCALE_DOWN = ('up', 'down')

    CPU = ('cpu')

    ATTRIBUTES = (
        ALARM_URL,
    ) = (
        'AlarmUrl',
    )

    properties_schema = {
        SERVER_NAME: properties.Schema(
            properties.Schema.STRING,
            _('Name or ID of Server(OS::Nova::Server) to apply policy to.'),
            constraints=[
                constraints.CustomConstraint('nova.server')
            ],
            required=True
        ),
        SCALING_RESOURCE: properties.Schema(
            properties.Schema.STRING,
            _('Type of resource need to be scaled.'),
            update_allowed=True,
            constraints=[
                constraints.AllowedValues([CPU]),
            ],
            default=CPU
        ),
        SCALING_DIRECTION: properties.Schema(
            properties.Schema.STRING,
            _('Direction of adjustment.'),
            required=True,
            constraints=[
                constraints.AllowedValues([SCALE_UP, SCALE_DOWN]),
            ],
            update_allowed=True
        ),
        COOLDOWN: properties.Schema(
            properties.Schema.NUMBER,
            _('Cooldown period, in seconds.'),
            update_allowed=True
        ),
    }

    attributes_schema = {
        ALARM_URL: attributes.Schema(
            _("A signed url to handle the alarm. (Heat extension).")
        ),
    }

    def handle_create(self):
        super(ScalingPolicy, self).handle_create()
        self.resource_id_set(self._get_user_id())

    def handle_update(self, json_snippet, tmpl_diff, prop_diff):
        """If Properties has changed, update self.properties.

        This ensures we get the new values during any subsequent adjustment.
        """
        if prop_diff:
            LOG.info('updating %s Alarm' % self.name)
            self.properties = json_snippet.properties(self.properties_schema,
                                                      self.context)

            LOG.info('%s Alarm updated, ScalingResource=%s,'
                     'ScalingDirection=%s,'
                     ' Cooldown=%s' % (self.name,
                                       self.properties[self.SCALING_RESOURCE],
                                       self.properties[self.SCALING_DIRECTION],
                                       self.properties[self.COOLDOWN]))

    def handle_signal(self, details=None):
        if self.action in (self.SUSPEND, self.DELETE):
            msg = _('Cannot signal resource during %s') % self.action
            raise Exception(msg)

        # ceilometer sends details like this:
        # {u'alarm_id': ID, u'previous': u'ok', u'current': u'alarm',
        #  u'reason': u'...'})
        # in this policy we currently assume that this gets called
        # only when there is an alarm. But the template writer can
        # put the policy in all the alarm notifiers (nodata, and ok).
        #
        # our watchrule has upper case states so lower() them all.
        if details is None:
            alarm_state = 'alarm'
        else:
            alarm_state = details.get('current',
                                      details.get('state', 'alarm')).lower()

        LOG.info(_('%(name)s Alarm, new state %(state)s')
                 % {'name': self.name, 'state': alarm_state})

        if alarm_state != 'alarm':
            return

        # Raise NoActionRequired if scaling not allowed
        self._check_scaling_allowed()

        cooldown_reason = "Indeterminate"
        size_changed = False
        try:
            server_id = self.properties[self.SERVER_NAME]
            server = self.client_plugin('nova').get_server(server_id)

            vcpu_key = 'wrs-res:vcpus'
            # Value is a list that looks like : [min, current, max]
            vcpu_info = server.__getattr__(vcpu_key)
            vcpu_min = vcpu_info[0]
            vcpus = vcpu_info[1]
            vcpu_max = vcpu_info[2]
            scale_dir = self.properties[self.SCALING_DIRECTION]
            LOG.debug('%s Evaluating %d %d %d Server %s Resource %s %s' %
                      (self.name, vcpu_min, vcpus, vcpu_max, server.name,
                       self.properties[self.SCALING_RESOURCE],
                       self.properties[self.SCALING_DIRECTION]))
            if scale_dir == self.SCALE_DOWN and vcpu_min == vcpus:
                cooldown_reason = _('Server %(name)s %(res)s'
                                    ' %(dir)s already at min %(val)d') % {
                    'name': server.name,
                    'res': self.properties[self.SCALING_RESOURCE],
                    'dir': self.properties[self.SCALING_DIRECTION],
                    'val': vcpu_min}
                LOG.info("Scale rejected due to %s" % cooldown_reason)
            elif scale_dir == self.SCALE_UP and vcpu_max == vcpus:
                cooldown_reason = _('Server %(name)s %(res)s'
                                    ' %(dir)s already at max %(val)d') % {
                    'name': server.name,
                    'res': self.properties[self.SCALING_RESOURCE],
                    'dir': self.properties[self.SCALING_DIRECTION],
                    'val': vcpu_max}
                LOG.info("Scale rejected due to %s" % cooldown_reason)
            else:
                try:
                    cooldown_reason = _('Server %(name)s %(res)s'
                                        ' %(dir)s accepted') % {
                        'name': server.name,
                        'res': self.properties[self.SCALING_RESOURCE],
                        'dir': self.properties[self.SCALING_DIRECTION]}
                    LOG.info("Scale  %s" % cooldown_reason)
                    server.scale(self.properties[self.SCALING_RESOURCE],
                                 self.properties[self.SCALING_DIRECTION])
                    size_changed = True
                except Exception as scale_ex:
                    cooldown_reason = _('Server %(name)s %(res)s'
                                        ' %(dir)s exception %(exc)s') % {
                        'name': server.name,
                        'res': self.properties[self.SCALING_RESOURCE],
                        'dir': self.properties[self.SCALING_DIRECTION],
                        'exc': str(scale_ex)}
                    LOG.error("Scale %s" % cooldown_reason)
        finally:
            # Set cooldown even if skipped adjustment due to being at boundary
            self._finished_scaling(cooldown_reason, size_changed)

    def _resolve_attribute(self, name):
        # heat extension: "AlarmUrl" returns the url to post to the policy
        # when there is an alarm.
        if self.resource_id is None:
            return
        if name == self.ALARM_URL:
            return six.text_type(self._get_ec2_signed_url())

    def get_reference_id(self):
        return resource.Resource.get_reference_id(self)


def resource_mapping():
    return {
        'OS::WR::ScalingPolicy': ScalingPolicy
    }
