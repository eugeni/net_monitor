#!/usr/bin/python

import gobject
import gtk
import pango

import gc
import os
from stat import *
import datetime
import getopt
import sys
import traceback

# for address
import socket
import fcntl
import struct

import time

import textwrap

# localization
import gettext
try:
    gettext.install("msec")
except IOError:
    _ = str

ifaces = {}
HISTOGRAM_SIZE=50


def get_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mac=_("No physical address")
    # ip address
    try:
        addr=socket.inet_ntoa(fcntl.ioctl( s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])
    except:
        addr=_("No address assigned")
    # mac address
    try:
        mac_struct=fcntl.ioctl( s.fileno(), 0x8927, struct.pack('256s', ifname[:15]))[18:24]
        mac=":".join(["%02x" % ord(char) for char in mac_struct])
    except:
        addr=_("No address assigned")
    # addr, mac
    return addr, mac

def readnet():
    """Reads values from /proc/net/dev"""
    net = {}
    data = open("/proc/net/dev").readlines()[2:]
    for l in data:
        dev, vals = l.split(":")
        dev = dev.strip()
        vals = vals.split()
        net[dev] = vals
    return net

def get_traffic(iface):
    net = readnet()
    if iface in net:
        bytes_in = int(net[iface][0])
        bytes_out = int(net[iface][8])
    else:
        bytes_in = 0
        bytes_out = 0
    return bytes_in, bytes_out

def format_size(size):
    """Pretty-Formats size"""
    return size

# borrowed from gnome-network-monitor 0.9.1 (gnetworkmonitor.sourceforge.net)
class LoadGraph:
    """
    This class is able do display a nicely formatted graph if interface
    bandwidth load.
    """
    # we don't want to allow the window to shrink below this height
    min_height = 70
    padding = { "left" : 50, "right" : 10, "top" : 10, "bottom" : 10 }
    colors  = ( "bg", "bg_outer", "in", "out" )

    def __init__(self, widget, hist, size):
        """
        widget   => GtkDrawingArea we paint into
        hist     => a list of integers containing the hist of incoming traffic
        width, height => initial size of the GtkDrawingArea widget
        """
        # set the minimum height of the widget
        widget.set_size_request(-1, 70)

        # the object holding the history and its size
        self.__hist = hist
        self.__size = size

        # strings holding 0, middle and max values for displayed graph
        self.__str_min = "0"
        self.__str_mid = ""     # gets computed later
        self.__str_max = ""     # gets computer later

        # size of the GtkDrawingArea
        self.__rect = self.__inner = gtk.gdk.Rectangle()
        self.maxval = 0                     # maximum value in the history
        self.__mesh_x = self.__mesh_y = 0   # distance in pixels between items
        self.__get_max()
        self.__on_size(widget.get_allocation())

        # save reference to the widget we paint into
        self.__widget = widget

        # lists holding bandwidth history mapped to actual coordinates
        self.__in  = list()
        self.__out = list()

        self.__colors = dict()
        self.set_color(bg=(0, 0, 0), fg_in=(255, 0, 0), fg_out=(0, 255, 0))
        self.__context = None

    def __set_context_color(self, con, col_tuple):
        """ Cleaner might be to extend the context class, but who cares?  """
        con.set_source_rgb(col_tuple[0], col_tuple[1], col_tuple[2])

    def __draw(self):
        """ Strokes the rectangles and draws the curves """
        if (self.__context == None):
            return
        # stroke the outer rectangle
        self.__context.rectangle(0, 0, self.__rect.width, self.__rect.height)
        self.__set_context_color(self.__context, self.__colors["bg"])
        self.__context.fill_preserve()
        self.__context.stroke()

        # stroke the inner rectangle
        self.__context.rectangle(self.__inner.x,
                                 self.__inner.y,
                                 self.__inner.width,
                                 self.__inner.height)
        self.__set_context_color(self.__context, self.__colors["bg"])
        self.__context.fill_preserve()
        self.__context.stroke()

        # stroke the quad around
        self.__context.move_to(self.__inner.x, self.__inner.y + self.__inner.height)
        self.__context.line_to(self.__inner.x, self.__inner.y)
        self.__context.line_to(self.__inner.x + self.__inner.width - self.__mesh_x, self.__inner.y)
        self.__context.line_to(self.__inner.x + self.__inner.width - self.__mesh_x, self.__inner.y + self.__inner.height)
        self.__set_context_color(self.__context, (255, 255, 255))
        self.__context.stroke()

        # draw the actual bandwidth curves
        self.__draw_bw(self.__in, self.__colors["fg_in"])
        self.__draw_bw(self.__out, self.__colors["fg_out"])

        # draw minimum, middle and max numbers
        self.__draw_num(self.__inner.height + self.__inner.y, self.__str_min, (255, 255, 255))
        self.__draw_num(self.__rect.height/2, self.__str_mid, (255, 255, 255))
        self.__draw_num(self.__inner.y, self.__str_max, (255, 255, 255))

    def __draw_num(self, ypos, num, color):
        """
        The leftmost column is used to draw info about maximum, minimum
        and average bw
        """
        self.__context.move_to(5, ypos)
        self.__context.show_text(num)
        self.__set_context_color(self.__context, color)
        self.__context.stroke()

    def __draw_bw(self, bw_list, color):
        """ Draws a curve from points stored in bw_list in color """
        self.__context.move_to(self.__inner.x, self.__inner.y + self.__inner.height)
        self.__set_context_color(self.__context, color)

        x = self.__inner.x + self.__mesh_x
        for i in bw_list[1:]:
            self.__context.line_to(x, i)
            x += self.__mesh_x
        self.__context.stroke()

    def __convert_one_hist(self, hist):
        """
        Maps values from one history object to real coordinates of the
        drawing area
        """
        converted = list()

        if self.__mesh_y == 0:
            return [self.__inner.height + self.__inner.y] * len(hist)

        for item in hist:
            if item <= 100: item = 0     # treshold to get rid of really small peaks
            converted.append((self.__inner.height - int(item / self.__mesh_y)) + self.__inner.y)
        return converted

    def __convert_points(self):
        """
        The bandwidth history object has the bandwidth stored as bytes. This method
        converts the bytes into actual coordiantes of the rectangle displayed
        """
        # compute the aspect ratio
        self.__mesh_x = float(self.__inner.width) / float(self.__size)
        self.__mesh_y = float(self.maxval) / float(self.__inner.height)

        self.__in  = self.__convert_one_hist(self.__hist["in"])
        self.__out = self.__convert_one_hist(self.__hist["out"])

    def __get_max(self):
        """ Finds the maximum value in both incoming and outgoing queue  """
        if self.__hist["in"]:
            maxin = max(self.__hist["in"])
        else:
            maxin = 0
        if self.__hist["out"]:
            maxout = max(self.__hist["out"])
        else:
            maxout = 0
        self.maxval = max(maxin, maxout)

    def __text_size(self):
        """ Computes the size of the text and thus the left border """
        val = self.maxval
        if val == 0 and self.maxval != 0:
            val = self.maxval

        self.__str_max = "%d %s" % (val, _("Bytes"))
        self.__str_mid = "%d %s" % (val/2, _("Bytes"))
        LoadGraph.padding["left"] = self.__context.text_extents(self.__str_max)[2] + 10

    def __on_size(self, rect):
        """ rect => a rectangle holding the size of the widget """
        self.__rect  = rect

        self.__inner.x = LoadGraph.padding["left"]
        self.__inner.y = LoadGraph.padding["top"]
        self.__inner.width = rect.width - LoadGraph.padding["right"] - self.__inner.x
        self.__inner.height = rect.height - LoadGraph.padding["bottom"] - self.__inner.y

        self.__convert_points()

    def on_expose(self, widget, event):
        """ A signal handler that is called every time we need to redraw
        the widget """
        self.__context = widget.window.cairo_create()

        self.__get_max()
        self.__text_size()
        self.__on_size(widget.get_allocation())

        self.__draw()

        return False

    def set_history(self, hist):
        """ Called typically on change of interface displayed """
        self.__hist = hist
        self.__convert_points()

    def update(self):
        """ Redraws the area """
        alloc = self.__widget.get_allocation()
        self.__widget.queue_draw_area(0, 0, alloc.width, alloc.height)

    def change_colors(self, col_in = None, col_out = None):
        """ Sets the colors to draw the curves with """
        if ( col_in )  : self.__colors["fg_in"] = col_in
        if ( col_out ) : self.__colors["fg_out"] = col_out

    def set_color(self, *args, **kwargs):
        """ Sets the colors of the graph """
        for key, value in kwargs.items():
            self.__colors[key] = value

class Monitor:
    def __init__(self):
        self.window = gtk.Window()
        self.window.set_title(_("Network monitor"))
        self.window.set_default_size(640, 440)
        self.window.connect('delete-event', lambda *w: gtk.main_quit())

        self.main_vbox = gtk.VBox()
        self.window.add(self.main_vbox)

        # notebook
        self.notebook = gtk.Notebook()
        self.main_vbox.pack_start(self.notebook)
        #self.notebook.connect('switch-page', self.show_net_status)

        self.ifaces = readnet()
        self.enabled_ifaces = []

        sorted_ifaces = self.ifaces.keys()
        sorted_ifaces.sort()

        for iface in sorted_ifaces:
            data_in, data_out = get_traffic(iface)
            self.ifaces[iface] = {'data_in': 0,
                              'data_out': 0,
                              'total_in': 0,
                              'total_out': 0,
                              'widget_in': None,
                              'widget_out': None,
                              'widget_speed_in': None,
                              'widget_speed_out': None,
                              'widget_histo_in': None,
                              'widget_histo_out': None,
                              'graph': None,
                              'histogram': [],
                              'address': "",
                              }
            iface_stat = self.build_iface_stat(iface)
            self.notebook.append_page(iface_stat, gtk.Label(iface))
            if self.check_network_accounting(iface):
                self.enabled_ifaces.append(iface)

        # configure timer
        gobject.timeout_add(1000, self.update)

        self.window.show_all()

    def update(self, interval=1):
        """Updates traffic counters (interval is in seconds)"""
        for iface in self.ifaces:
            old_data_in = self.ifaces[iface]['data_in']
            old_data_out = self.ifaces[iface]['data_out']
            total_in = self.ifaces[iface]['total_in']
            total_out = self.ifaces[iface]['total_out']
            data_in, data_out = get_traffic(iface)
            # is it the first measure?
            if old_data_in == 0 and old_data_out == 0:
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
            # calculating histogram
            histogram_in = self.ifaces[iface]['histogram']['in']
            histogram_out = self.ifaces[iface]['histogram']['out']
            if histogram_in:
                histo_in = reduce(lambda x, y: x+y, histogram_in) / HISTOGRAM_SIZE
            else:
                histo_in = 0
            if histogram_out:
                histo_out = reduce(lambda x, y: x+y, histogram_out) / HISTOGRAM_SIZE
            else:
                histo_out = 0
            # update saved values
            self.ifaces[iface]['data_in'] = data_in
            self.ifaces[iface]['data_out'] = data_out
            self.ifaces[iface]['total_in'] = total_in
            self.ifaces[iface]['total_out'] = total_out
            # update widgets
            ip, mac = get_address(iface)
            for widget, value in [('widget_in', total_in),
                                  ('widget_out', total_out),
                                  ('widget_speed_in', speed_in),
                                  ('widget_speed_out', speed_out),
                                  ('widget_histo_in', histo_in),
                                  ('widget_histo_out', histo_out),
                                  ('widget_ip_address', ip),
                                  ('widget_hw_address', mac),
                                  ]:
                if widget in self.ifaces[iface]:
                    self.ifaces[iface][widget].set_text(str(value))
                else:
                    print "%s not found in %s" % (widget, iface)
            # updating graph
            hist_in = self.ifaces[iface]['histogram']['in']
            hist_in.append(speed_in)
            if len(hist_in) > HISTOGRAM_SIZE:
                del hist_in[0]
            hist_out = self.ifaces[iface]['histogram']['out']
            hist_out.append(speed_out)
            if len(hist_out) > HISTOGRAM_SIZE:
                del hist_out[0]
            graph = self.ifaces[iface]['graph']
            graph.update()
        gobject.timeout_add(interval * 1000, self.update)

    def check_network_accounting(self, iface):
        """Checks if network accounting was enabled on interface"""
        try:
            os.stat("/var/lib/vnstat/%s" % iface)
            return True
        except:
            return False

    def show_statistics_dialog(self, widget, iface):
        """Shows statistics dialog"""
        dialog = gtk.Dialog(_("Network statistics for %s") % iface,
                self.window, 0,
                (gtk.STOCK_OK, gtk.RESPONSE_OK)
                )
        # statistics vbox
        stats_vbox = dialog.vbox
        if self.check_network_accounting(iface):
            # graph
            graph_vnstat = gtk.Image()
            pixbuf = self.load_graph_from_vnstat(iface, type="summary")
            graph_vnstat.set_from_pixbuf(pixbuf)
            stats_vbox.pack_start(graph_vnstat)
            # buttons
            frame = gtk.Frame(_("Network traffic statistics for %s") % iface)
            stats_vbox.add(frame)
            vbox = gtk.VBox()
            frame.add(vbox)
            # summary
            button = gtk.RadioButton(None, _("Summary"))
            button.connect('toggled', self.update_stat_iface, (iface, graph_vnstat, "summary"))
            vbox.pack_start(button, False, False)
            # summary
            button = gtk.RadioButton(button, _("Hourly traffic"))
            button.connect('toggled', self.update_stat_iface, (iface, graph_vnstat, "hourly"))
            vbox.pack_start(button, False, False)
            # summary
            button = gtk.RadioButton(button, _("Daily traffic"))
            button.connect('toggled', self.update_stat_iface, (iface, graph_vnstat, "daily"))
            vbox.pack_start(button, False, False)
            # summary
            button = gtk.RadioButton(button, _("Monthly traffic"))
            button.connect('toggled', self.update_stat_iface, (iface, graph_vnstat, "monthly"))
            vbox.pack_start(button, False, False)
            # summary
            button = gtk.RadioButton(button, _("Top 10 traffic days"))
            button.connect('toggled', self.update_stat_iface, (iface, graph_vnstat, "top"))
            vbox.pack_start(button, False, False)
        else:
            label = gtk.Label(_("Network accounting was not enabled on interface %s.\nPlease enable network accounting on the interface in order to view traffic statistics."))
            stats_vbox.add(label)

        stats_vbox.show_all()
        ret = dialog.run()
        dialog.destroy()

    def build_iface_stat(self, iface):
        """Builds graphical view for interface"""
        traf_vbox = gtk.VBox()
        # graph
        draw = gtk.DrawingArea()
        traf_vbox.pack_start(draw)
        histogram = {"in": [], "out": []}
        graph = LoadGraph(draw, histogram, HISTOGRAM_SIZE)
        draw.connect('expose_event', graph.on_expose)
        self.ifaces[iface]['graph'] = graph
        self.ifaces[iface]['histogram'] = histogram

        frame_global = gtk.Frame(_("Interface settings"))
        traf_vbox.pack_start(frame_global, False, False)
        vbox_global = gtk.VBox(spacing=5)
        frame_global.add(vbox_global)
        # configuring callbacks
        sizegroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        # interface
        iface_h, iface_p = self.build_value_pair(sizegroup, _("Network interface:"), iface)
        vbox_global.pack_start(iface_h, False, False)
        iface_s, iface_status = self.build_value_pair(sizegroup, _("Device status:"), _("Up"))
        vbox_global.pack_start(iface_s, False, False)
        iface_addr_s, iface_addr = self.build_value_pair(sizegroup, _("IP Address:"))
        self.ifaces[iface]["widget_ip_address"] = iface_addr
        vbox_global.pack_start(iface_addr_s, False, False)
        iface_mac_s, iface_mac = self.build_value_pair(sizegroup, _("Hardware address:"))
        self.ifaces[iface]["widget_hw_address"] = iface_mac
        vbox_global.pack_start(iface_mac_s, False, False)

        # traffic
        frame = gtk.Frame(_("Traffic statistics"))
        traf_vbox.pack_start(frame)
        vbox = gtk.VBox(spacing=5)
        frame.add(vbox)
        total_in_h, total_in = self.build_value_pair(sizegroup, _("Received data:"))
        self.ifaces[iface]["widget_in"] = total_in
        vbox.pack_start(total_in_h, False, False)
        total_out_h, total_out = self.build_value_pair(sizegroup, _("Sent data:"))
        self.ifaces[iface]["widget_out"] = total_out
        vbox.pack_start(total_out_h, False, False)
        speed_in_h, speed_in = self.build_value_pair(sizegroup, _("Download speed:"))
        self.ifaces[iface]["widget_speed_in"] = speed_in
        vbox.pack_start(speed_in_h, False, False)
        speed_out_h, speed_out = self.build_value_pair(sizegroup, _("Upload speed:"))
        self.ifaces[iface]["widget_speed_out"] = speed_out
        vbox.pack_start(speed_out_h, False, False)
        histo_in_h, histo_in = self.build_value_pair(sizegroup, _("Average download speed (over past %d samples):") % HISTOGRAM_SIZE)
        self.ifaces[iface]["widget_histo_in"] = histo_in
        vbox.pack_start(histo_in_h, False, False)
        histo_out_h, histo_out = self.build_value_pair(sizegroup, _("Average upload speed (over past %d samples):") % HISTOGRAM_SIZE)
        self.ifaces[iface]["widget_histo_out"] = histo_out
        vbox.pack_start(histo_out_h, False, False)

        # statistics button
        if self.check_network_accounting(iface):
            button = gtk.Button(_("Show detailed network statistics"))
            button.connect('clicked', self.show_statistics_dialog, iface)
            traf_vbox.pack_start(button, False, False)
        else:
            label = gtk.Label("\n".join(textwrap.wrap(_("Network accounting is not enabled for this interface. Please enable it in Mandriva network center in order to view detailed traffic statistics"))))
            traf_vbox.pack_start(label, False, False)

        return traf_vbox

    def build_value_pair(self, sizegroup, text, value_text=None):
        """Builds a value pair"""
        hbox = gtk.HBox(spacing=10)
        name = gtk.Label(text)
        name.set_property("xalign", 1.0)
        hbox.pack_start(name, False, False)
        value = gtk.Label(value_text)
        value.set_property("xalign", 0.0)
        hbox.pack_start(value, False, False)
        sizegroup.add_widget(name)
        return hbox, value

    def update_stat_iface(self, widget, data):
        """Updates graphic statistics"""
        iface, graph, type = data
        pixbuf = self.load_graph_from_vnstat(iface, type)
        graph.set_from_pixbuf(pixbuf)

    def load_graph_from_vnstat(self, iface, type="hourly"):
        """Loads graph from vnstat. Right now uses vnstati to do all the dirty job"""
        # load image from data
        if type == "hourly":
            param="-h"
        elif type == "monthly":
            param="-m"
        elif type == "daily":
            param="-d"
        elif type == "top":
            param="-t"
        elif type == "summary":
            param="-s"
        else:
            # show summary if parameter is unknown
            print "Unknown parameter %s, showing summary.." % type
            param="-s"
        data = os.popen("vnstati %s -o - -i %s" % (param, iface)).read()
        loader = gtk.gdk.PixbufLoader()
        loader.write(data)
        loader.close()
        pixbuf = loader.get_pixbuf()
        return pixbuf

if __name__ == "__main__":
    monitor = Monitor()
    gtk.main()
