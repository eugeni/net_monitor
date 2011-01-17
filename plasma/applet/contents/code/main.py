# -*- coding: utf-8 -*-
# Net_monitor plasma interface
#
# Copyright, (C) Eugeni Dodonov <eugeni@mandriva.com>, 2011
#

from PyQt4.QtCore import Qt, QString, pyqtSignature
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
        self.resize(125, 125)
        self.setAspectRatioMode(Plasma.Square)

        self.connectToEngine()

    def connectToEngine(self):
        self.engine = self.dataEngine("net_monitor_data")
        print "Engine: %s" % self.engine
        self.sources = self.engine.sources()
        for source in self.sources:
            print "Will monitor %s" % source
            self.engine.connectSource(source, self, 1000)

    @pyqtSignature("dataUpdated(const QString &, const Plasma::DataEngine::Data &)")
    def dataUpdated(self, sourceName, data):
        """Got something from data source"""
        print "Updating device %s" % sourceName
        for item in ["data_in", "data_out", "total_in", "total_out"]:
            print "%s %s" % (item, data[QString(item)])

    def paintInterface(self, painter, option, rect):
        painter.save()
        painter.setPen(Qt.black)
        painter.drawText(rect, Qt.AlignVCenter | Qt.AlignHCenter, "Hello net_monitor!")
        painter.restore()
 
def CreateApplet(parent):
    return NetMonitor(parent)
