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

import croniter
import eventlet
import netaddr
import pytz
import six

from oslo_utils import netutils
from oslo_utils import timeutils

from heat.common.i18n import _
from heat.common import netutils as heat_netutils
from heat.engine import constraints


class TestConstraintDelay(constraints.BaseCustomConstraint):

    def validate_with_client(self, client, value):
        eventlet.sleep(value)


class IPConstraint(constraints.BaseCustomConstraint):

    # is_valid_ip in oslo_utils simply calls netaddr validation
    # netaddr considers 1.2.3 and 1.2 to be valid ipv4 addresses
    # This code makes ipv4 require at least 3 dots
    def is_valid_ipv4(self, address):
        if isinstance(address, six.string_types):
            if address.count('.') != 3:
                return False
        return netutils.is_valid_ipv4(address)

    def is_valid_ipv6(self, address):
        return netutils.is_valid_ipv6(address)

    def validate(self, value, context, template=None):
        self._error_message = 'Invalid IP address'
        if not isinstance(value, six.string_types):
            return False
        return self.is_valid_ipv4(value) or self.is_valid_ipv6(value)


class MACConstraint(constraints.BaseCustomConstraint):

    def validate(self, value, context, template=None):
        self._error_message = 'Invalid MAC address.'
        return netaddr.valid_mac(value)


class DNSNameConstraint(constraints.BaseCustomConstraint):

    def validate(self, value, context):
        try:
            heat_netutils.validate_dns_format(value)
        except ValueError as ex:
            self._error_message = ("'%(value)s' not in valid format."
                                   " Reason: %(reason)s") % {
                                       'value': value,
                                       'reason': six.text_type(ex)}
            return False
        return True


class RelativeDNSNameConstraint(DNSNameConstraint):

    def validate(self, value, context):
        if not value:
            return True
        if value.endswith('.'):
            self._error_message = _("'%s' is a FQDN. It should be a "
                                    "relative domain name.") % value
            return False

        length = len(value)
        if length > heat_netutils.FQDN_MAX_LEN - 3:
            self._error_message = _("'%(value)s' contains '%(length)s' "
                                    "characters. Adding a domain name will "
                                    "cause it to exceed the maximum length "
                                    "of a FQDN of '%(max_len)s'.") % {
                                        "value": value,
                                        "length": length,
                                        "max_len": heat_netutils.FQDN_MAX_LEN}
            return False

        return super(RelativeDNSNameConstraint, self).validate(value, context)


class DNSDomainConstraint(DNSNameConstraint):

    def validate(self, value, context):
        if not value:
            return True

        if not super(DNSDomainConstraint, self).validate(value, context):
            return False
        if not value.endswith('.'):
            self._error_message = ("'%s' must end with '.'.") % value
            return False

        return True


class CIDRConstraint(constraints.BaseCustomConstraint):

    def _validate_whitespace(self, data):
        self._error_message = ("Invalid net cidr '%s' contains "
                               "whitespace" % data)
        if len(data.split()) > 1:
            return False
        return True

    def _validate_ip(self, data, context, template):
        chunks = data.split('/')
        if len(chunks) > 1:
            ipaddr = chunks[0]
            if not IPConstraint().validate(ipaddr, context, template):
                raise ValueError('invalid IPNetwork %s' % data)
        return True

    def validate(self, value, context, template=None):
        try:
            netaddr.IPNetwork(value, implicit_prefix=True)
            self._validate_ip(value, context, template)
            return self._validate_whitespace(value)
        except Exception as ex:
            self._error_message = 'Invalid net cidr %s ' % six.text_type(ex)
            return False


class ISO8601Constraint(constraints.BaseCustomConstraint):

    def validate(self, value, context, template=None):
        try:
            timeutils.parse_isotime(value)
        except Exception:
            return False
        else:
            return True


class CRONExpressionConstraint(constraints.BaseCustomConstraint):

    def validate(self, value, context, template=None):
        if not value:
            return True
        try:
            croniter.croniter(value)
            return True
        except Exception as ex:
            self._error_message = _(
                'Invalid CRON expression: %s') % six.text_type(ex)
        return False


class TimezoneConstraint(constraints.BaseCustomConstraint):

    def validate(self, value, context, template=None):
        if not value:
            return True
        try:
            pytz.timezone(value)
            return True
        except Exception as ex:
            self._error_message = _(
                'Invalid timezone: %s') % six.text_type(ex)
        return False


class ExpirationConstraint(constraints.BaseCustomConstraint):

    def validate(self, value, context):
        if not value:
            return True
        try:
            expiration_tz = timeutils.parse_isotime(value.strip())
            expiration = timeutils.normalize_time(expiration_tz)
            if expiration > timeutils.utcnow():
                return True
            raise ValueError(_('Expiration time is out of date.'))
        except Exception as ex:
            self._error_message = (_(
                'Expiration {0} is invalid: {1}').format(value,
                                                         six.text_type(ex)))
        return False
