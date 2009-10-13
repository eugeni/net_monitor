#!/usr/bin/python
"""net_monitor: wifi monitoring"""

import os
import socket
import fcntl
import struct
import traceback
import array

# native librari implements a few bits
import _native


class Monitor:
    # based on http://svn.pardus.org.tr/pardus/tags/pardus-1.0/system/base/wireless-tools/comar/link.py

    # wireless IOCTL constants
    SIOCGIWMODE = 0x8B07    # get operation mode
    SIOCGIWRATE = 0x8B21    # get default bit rate
    SIOCGIWESSID = 0x8B1B   # get essid

    # wireless modes
    modes = ['Auto', 'Ad-Hoc', 'Managed', 'Master', 'Repeat', 'Second', 'Monitor']

    # constants
    SIZE_KB=1000
    SIZE_MB=1000**2
    SIZE_GB=1000**3

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.net = {}

    def ioctl(self, func, params):
        return fcntl.ioctl(self.sock.fileno(), func, params)

    def wifi_ioctl(self, iface, func, arg=None):
        """Prepares some variables for wifi and runs ioctl"""
        if not arg:
            data = (iface + '\0' * 32)[:32]
        else:
            data = (iface + '\0' * 16)[:16] + arg
        try:
            res = self.ioctl(func, data)
            return res
        except:
            return None

    def wifi_get_max_quality(self, iface):
        """Gets maximum quality value"""
        return _native.wifi_get_max_quality(iface)

    def wifi_get_ap(self, iface):
        """Gets access point address"""
        return _native.wifi_get_ap(iface)

    def wifi_get_essid(self, iface):
        """Get current essid for an interface"""
        buffer = array.array('c', '\0' * 16)
        addr, length = buffer.buffer_info()
        arg = struct.pack('Pi', addr, length)
        self.wifi_ioctl(iface, self.SIOCGIWESSID, arg)
        return buffer.tostring().strip('\0')

    def wifi_get_mode(self, iface):
        """Get current mode from an interface"""
        result = self.wifi_ioctl(iface, self.SIOCGIWMODE)
        if not result:
            return _("Unknown")
        mode = struct.unpack("i", result[16:20])[0]
        return self.modes[mode]

    def wifi_get_bitrate(self, iface):
        """Gets current operating rate from an interface"""
        # Note: KILO is not 2^10 in wireless tools world

        result = self.wifi_ioctl(iface, self.SIOCGIWRATE)

        if result:
            size = struct.calcsize('ihbb')
            m, e, i, pad = struct.unpack('ihbb', result[16:16+size])
            if e == 0:
                bitrate =  m
            else:
                bitrate = float(m) * 10**e
            return bitrate
        else:
            return 0

    def get_status(self, ifname):
        try:
            with open("/sys/class/net/%s/operstate" % ifname) as fd:
                status = fd.readline().strip()
        except:
            status="unknown"
        if status == "unknown":
            # pretty-format interface status
            status = _("Unknown")
        return status

    def wireless_stats(self):
        """Check if device is wireless and get its details if necessary"""
        try:
            stats = {}
            with open("/proc/net/wireless") as fd:
                ifaces = fd.readlines()[2:]
            for line in ifaces:
                line = line.strip()
                if not line:
                    continue
                iface, params = line.split(":", 1)
                iface = iface.strip()
                params = params.replace(".", "").split()
                link = int(params[1])
                stats[iface] = link
            return stats
        except:
            # something bad happened
            traceback.print_exc()
            return {}

    def has_wireless(self, iface):
        """Checks if device has wireless capabilities"""
        return os.access("/sys/class/net/%s/wireless" % iface, os.R_OK)

    def get_address(self, ifname):
        mac=_("No physical address")
        # ip address
        try:
            res = self.ioctl(0x8915, struct.pack('256s', ifname[:15]))[20:24]
            addr=socket.inet_ntoa(res)
        except:
            addr=_("No address assigned")
        # mac address
        try:
            mac_struct=self.ioctl(0x8927, struct.pack('256s', ifname[:15]))[18:24]
            mac=":".join(["%02x" % ord(char) for char in mac_struct])
        except:
            addr=_("No address assigned")
        # addr, mac
        return addr, mac

    def readnet(self):
        """Reads values from /proc/net/dev"""
        net = {}
        try:
            with open("/proc/net/dev") as fd:
                data = fd.readlines()[2:]
            for l in data:
                dev, vals = l.split(":")
                dev = dev.strip()
                vals = vals.split()
                net[dev] = vals
        except:
            traceback.print_exc()
        return net

    def get_traffic(self, iface, net=None):
        if not net:
            if not self.net:
                self.readnet()
            net = self.net
        if iface in net:
            bytes_in = int(net[iface][0])
            bytes_out = int(net[iface][8])
        else:
            bytes_in = 0
            bytes_out = 0
        return bytes_in, bytes_out

    def format_size(self, size, opt=""):
        """Pretty-Formats size"""
        # convert to float
        size_f = size * 1.0
        pretty_size = None
        pretty_bytes = "%d Bytes%s" % (size, opt)
        if size > self.SIZE_GB:
            pretty_size = "%0.2f GB%s" % (size_f / self.SIZE_GB, opt)
        elif size > self.SIZE_MB:
            pretty_size = "%0.2f MB%s" % (size_f / self.SIZE_MB, opt)
        elif size > self.SIZE_KB:
            pretty_size = "%0.2f KB%s" % (size_f / self.SIZE_KB, opt)
        else:
            pretty_size = pretty_bytes
        return pretty_size, pretty_bytes

    def get_dns(self):
        """Returns list of DNS servers"""
        servers = []
        try:
            with open("/etc/resolv.conf") as fd:
                data = fd.readlines()
            for l in data:
                l = l.strip()
                if not l:
                    continue
                fields = l.split()
                if fields[0] == 'nameserver':
                    servers.append(fields[1])
        except:
            traceback.print_exc()
        return servers

    def get_routes(self):
        """Read network routes"""
        routes = []
        default_routes = []
        try:
            with open("/proc/net/route") as fd:
                data = fd.readlines()[1:]
            for l in data:
                l = l.strip()
                if not l:
                    continue
                params = l.split()
                iface = params[0]
                dst = int(params[1], 16)
                gw = int(params[2], 16)
                gw_str = socket.inet_ntoa(struct.pack("L", gw))
                metric = int(params[6], 16)
                mask = int(params[7], 16)
                routes.append((iface, dst, mask, gw, metric))
                if dst == 0 and mask == 0:
                    default_routes.append((gw_str, iface))
        except:
            traceback.print_exc()
            pass
        return routes, default_routes

