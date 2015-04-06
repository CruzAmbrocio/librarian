"""
plugin.py: Network interfaces plugin

Display all available network interfaces on device.

Copyright 2014-2015, Outernet Inc.
Some rights reserved.

This software is free software licensed under the terms of GPLv3. See COPYING
file that comes with the source code, or http://www.gnu.org/licenses/gpl.txt.
"""

from bottle_utils.i18n import lazy_gettext as _

from ..dashboard import DashboardPlugin

from .lsnet import get_network_interfaces


def install(app, route):
    pass


class Dashboard(DashboardPlugin):
    # Translators, used as dashboard section title
    heading = _('Network interfaces')
    name = 'netinterfaces'

    def get_context(self):
        interfaces = sorted(get_network_interfaces(), key=lambda x: x.index)
        return dict(interfaces=interfaces)