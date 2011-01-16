# -*- coding: utf-8 -*-
# Net_monitor plasma data source
#
# Copyright, (C) Eugeni Dodonov <eugeni@mandriva.com>, 2011
#

from PyQt4.QtCore import Qt, QVariant
from PyKDE4.plasma import Plasma
from PyKDE4 import plasmascript

# localization
import gettext
try:
    gettext.install("net_monitor")
except IOError:
    _ = str

from net_monitor import Monitor
 
class NetMonitorDataEngine(plasmascript.DataEngine):
    def __init__(self,parent,args=None):
        plasmascript.DataEngine.__init__(self,parent)

    def init(self):
        """Initialize Monitor class"""

        self.setMinimumPollingInterval(333)

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
                #print "%s - %s - %s - %s - %s - %s" % (proto, loc_addr, loc_port, rem_addr, rem_port, status)
                pass

    def sources(self):
        """List of provided sources"""
        sources = self.ifaces.keys()
        print sources
        return sources

    def sourceRequestEvent(self, name):
        """Prepare source event"""
        self.refresh_connections()
        return self.updateSourceEvent(name)

    def updateSourceEvent(self, name):
        """Returns monitoring data"""
        print "Getting info for %s " % name
        net=self.monitor.readnet()
        interval = 1 # update interval
        wifi_stats = self.monitor.wireless_stats()
        for iface in [name]:
            iface = str(iface)
            status = self.monitor.get_status(iface)
            old_data_in = self.ifaces[iface]['data_in']
            old_data_out = self.ifaces[iface]['data_out']
            total_in = self.ifaces[iface]['total_in']
            total_out = self.ifaces[iface]['total_out']
            # get the uptime
            uptime = self.monitor.get_uptime(iface)
            # update widgets
            ip, mac = self.monitor.get_address(iface)
            device_exists, data_in, data_out = self.monitor.get_traffic(iface, net)
            # is it a wireless interface?
            if iface in self.wireless_ifaces:
                essid = self.monitor.wifi_get_essid(iface)
                mode = self.monitor.wifi_get_mode(iface)
                bitrate = self.monitor.wifi_get_bitrate(iface)
                ap = self.monitor.wifi_get_ap(iface)
                link = wifi_stats.get(iface, 0)
                # calculate link quality
                if "max_quality" in self.ifaces[iface]:
                    max_quality = self.ifaces[iface]["max_quality"]
                    if max_quality != 0:
                        quality = link * 100.0 / max_quality
                    else:
                        quality = 0
                else:
                    quality = 0
            else:
                essid = None
                mode = None
                bitrate = None
                ap = None
                quality = 0
            # is it the first measure?
            if old_data_in == 0 and old_data_out == 0:
                old_data_in = data_in
                old_data_out = data_out
            # check if device exists
            if not device_exists:
                old_data_in = data_in
                old_data_out = data_out
            # check total download
            diff_in = data_in - old_data_in
            diff_out = data_out - old_data_out
            # checking for 32bits overflow
            if diff_in < 0:
                diff_in += 2**32
            if diff_out < 0:
                diff_out += 2**32
            total_in += diff_in
            total_out += diff_out
            # speed
            speed_in = diff_in / interval
            speed_out = diff_out / interval
            # update saved values
            self.ifaces[iface]['data_in'] = data_in
            self.ifaces[iface]['data_out'] = data_out
            self.ifaces[iface]['total_in'] = total_in
            self.ifaces[iface]['total_out'] = total_out
            # now set the applet data
            self.setData(iface, "data_in", QVariant(data_in))
            self.setData(iface, "data_out", QVariant(data_in))
            self.setData(iface, "total_in", QVariant(data_in))
            self.setData(iface, "total_out", QVariant(data_in))
            for item, value in [('ip_address', ip),
                                  ('status', status),
                                  ('hw_address', mac),
                                  ('essid', essid),
                                  ('mode', mode),
                                  ('bitrate', bitrate),
                                  ('ap', ap),
                                  ('quality', "%d%%" % quality),
                                  ('widget_uptime', uptime),
                                  ]:
                self.setData(iface, item, QVariant(value))
            return True
 
def CreateDataEngine(parent):
    return NetMonitorDataEngine(parent)
