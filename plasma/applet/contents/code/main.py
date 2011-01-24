# -*- coding: utf-8 -*-
# Net_monitor plasma interface
#
# Copyright, (C) Eugeni Dodonov <eugeni@mandriva.com>, 2011
#

from PyQt4.QtCore import Qt, QString, pyqtSignature
from PyQt4.QtGui import QGraphicsLinearLayout
from PyKDE4.plasma import Plasma
from PyKDE4 import plasmascript

# localization
import gettext
try:
    gettext.install("net_monitor")
except IOError:
    _ = str

class NetMonitor(plasmascript.Applet):
    def __init__(self,parent,args=None):
        plasmascript.Applet.__init__(self,parent)

    def init(self):
        self.setHasConfigurationInterface(False)
        self.setAspectRatioMode(Plasma.Square)

        self.theme = Plasma.Svg(self)
        self.theme.setImagePath("widgets/background")
        self.setBackgroundHints(Plasma.Applet.DefaultBackground)

        self.layout = QGraphicsLinearLayout(Qt.Horizontal, self.applet)

        self.monitoring = {}
        self.widgets = {}
        for source in self.connectToEngine():
            label = Plasma.Label(self.applet)
            label.setText("%s:" % source)
            self.layout.addItem(label)
            self.widgets[str(source)] = label
            self.monitoring[str(source)] = {"in": 0, "out": 0}
        self.applet.setLayout(self.layout)

    def connectToEngine(self):
        self.engine = self.dataEngine("net_monitor_data")
        self.sources = self.engine.sources()
        for source in self.sources:
            self.engine.connectSource(source, self, 1000)
        return self.sources

    @pyqtSignature("dataUpdated(const QString &, const Plasma::DataEngine::Data &)")
    def dataUpdated(self, sourceName, data):
        """Got something from data source"""
        iface = str(sourceName)
        if iface not in self.widgets:
            print "Error: data for %s not available yet" % iface
            return
        widget = self.widgets[iface]
        data_in = int(data[QString("data_in")])
        data_out = int(data[QString("data_out")])
        old_data_in = self.monitoring[iface]["in"]
        old_data_out = self.monitoring[iface]["out"]
        if old_data_in == -1:
            speed_in = 0
        else:
            speed_in = data_in - old_data_in
        if old_data_out == -1:
            speed_out = 0
        else:
            speed_out = data_out - old_data_out
        self.monitoring[iface]["in"] = data_in
        self.monitoring[iface]["out"] = data_out
        widget.setText("%s\n\/: %d\n/\: %d" % (sourceName, speed_in, speed_out))

    def paintInterface(self, painter, option, rect):
        painter.save()
        painter.restore()
 
def CreateApplet(parent):
    return NetMonitor(parent)
