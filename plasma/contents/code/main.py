# -*- coding: utf-8 -*-
# Net_monitor plasma interface
#
# Copyright, (C) Eugeni Dodonov <eugeni@mandriva.com>, 2011
#

from PyQt4.QtCore import Qt
from PyKDE4.plasma import Plasma
from PyKDE4 import plasmascript

# localization
import gettext
try:
    gettext.install("net_monitor")
except IOError:
    _ = str

from net_monitor import Monitor
 
class NetMonitor(plasmascript.Applet):
    def __init__(self,parent,args=None):
        plasmascript.Applet.__init__(self,parent)

        self.monitor = Monitor()
        self.ifaces = self.monitor.readnet()

        self.enabled_ifaces = []
        self.wireless_ifaces = filter(self.monitor.has_wireless, self.ifaces.keys())

        sorted_ifaces = self.ifaces.keys()
        sorted_ifaces.sort()

        net=self.monitor.readnet()

        for iface in sorted_ifaces:
            device_exists, data_in, data_out = self.monitor.get_traffic(iface,net)
            self.ifaces[iface] = {'data_in': 0,
                              'data_out': 0,
                              'total_in': 0,
                              'total_out': 0,
                              'graph': None,
                              'histogram': [],
                              'address': "",
                              }
            if self.monitor.has_network_accounting(iface):
                self.enabled_ifaces.append(iface)

        self.refresh_connections()

    def refresh_connections(self):
        """Updates connections"""
        for proto in ["tcp", "udp"]:
            connections = self.monitor.get_connections(proto=proto)
            for loc_addr, loc_port, rem_addr, rem_port, status in connections:
                print "%s - %s - %s - %s - %s - %s" % (proto, loc_addr, loc_port, rem_addr, rem_port, status)


    def init(self):
        self.setHasConfigurationInterface(False)
        self.resize(125, 125)
        self.setAspectRatioMode(Plasma.Square)

    def paintInterface(self, painter, option, rect):
        painter.save()
        painter.setPen(Qt.black)
        painter.drawText(rect, Qt.AlignVCenter | Qt.AlignHCenter, "Hello net_monitor!")
        painter.restore()
 
def CreateApplet(parent):
    return NetMonitor(parent)
