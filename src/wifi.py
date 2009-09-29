#!/usr/bin/python
"""net_monitor: wifi monitoring"""

# native librari implements a few bits
import _native
import socket
import fcntl
import struct
import traceback
import array


class Wireless:
    # based on http://svn.pardus.org.tr/pardus/tags/pardus-1.0/system/base/wireless-tools/comar/link.py

    # wireless IOCTL constants
    SIOCGIWMODE = 0x8B07    # get operation mode
    SIOCGIWRATE = 0x8B21    # get default bit rate
    SIOCGIWESSID = 0x8B1B   # get essid

    # wireless modes
    modes = ['Auto', 'Ad-Hoc', 'Managed', 'Master', 'Repeat', 'Second', 'Monitor']

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def ioctl(self, func, params):
        return fcntl.ioctl(self.sock.fileno(), func, params)

    def get_max_quality(self, iface):
        """Gets maximum quality value"""
        return _native.wifi_get_max_quality(iface)

    def call(self, iface, func, arg=None):
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

    def get_essid(self, iface):
        """Get current essid for an interface"""
        buffer = array.array('c', '\0' * 16)
        addr, length = buffer.buffer_info()
        arg = struct.pack('Pi', addr, length)
        self.call(iface, self.SIOCGIWESSID, arg)
        return buffer.tostring().strip('\0')

    def get_mode(self, iface):
        """Get current mode from an interface"""
        result = self.call(iface, self.SIOCGIWMODE)
        mode = struct.unpack("i", result[16:20])[0]
        return self.modes[mode]

    def get_bitrate(self, iface):
        """Gets current operating rate from an interface"""
        # Note: KILO is not 2^10 in wireless tools world

        result = self.call(iface, self.SIOCGIWRATE)

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
