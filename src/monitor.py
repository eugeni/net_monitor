#!/usr/bin/python
"""net_monitor: wifi monitoring"""

# native librari implements a few bits
import _native
import socket
import fcntl
import struct
import traceback
import array


class Monitor:
    # based on http://svn.pardus.org.tr/pardus/tags/pardus-1.0/system/base/wireless-tools/comar/link.py

    # wireless IOCTL constants
    SIOCGIWMODE = 0x8B07    # get operation mode
    SIOCGIWRATE = 0x8B21    # get default bit rate
    SIOCGIWESSID = 0x8B1B   # get essid

    # wireless modes
    modes = ['Auto', 'Ad-Hoc', 'Managed', 'Master', 'Repeat', 'Second', 'Monitor']

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
            traceback.print_exc()
            return None

    def wifi_get_max_quality(self, iface):
        """Gets maximum quality value"""
        return _native.wifi_get_max_quality(iface)

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
            return -1

    def get_status(self, ifname):
        try:
            fd = open("/sys/class/net/%s/operstate" % ifname)
            status = fd.readline().strip()
            fd.close()
        except:
            status="unknown"
        if status == "unknown":
            # pretty-format interface status
            status = _("Unknown")
        return status

    def readwireless(self):
        """Check if device is wireless and get its details if necessary"""
        try:
            with open("/proc/net/wireless") as fd:
                ifaces = fd.readlines()[2:]
            for line in ifaces:
                line = line.strip()
                if not line:
                    continue
                iface, params = line.split(":", 1)
                iface = iface.strip()
                params = params.replace(".", "").split()
            return {}
        except:
            # something bad happened
            traceback.print_exc()
            return {}

    def get_address(self, ifname):
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

    def readnet(self):
        """Reads values from /proc/net/dev"""
        net = {}
        data = open("/proc/net/dev").readlines()[2:]
        for l in data:
            dev, vals = l.split(":")
            dev = dev.strip()
            vals = vals.split()
            net[dev] = vals
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

    def format_size(self, size):
        """Pretty-Formats size"""
        return size

