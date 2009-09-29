from version import *

from distutils.core import setup, Extension

module1 = Extension('net_monitor/_native',
                        sources=['src/_native.c'])

setup (name='net_monitor',
        version=version,
        description='Mandriva network monitoring tool',
        author="Eugeni Dodonov",
        author_email="eugeni@mandriva.com",
        url="http://www.mandriva.com",
        license="GPL",
        long_description=
"""\
This is a network monitoring tool for Mandriva Linux, intended to replace the
old net_monitor from drakx-net.  It supports graphical network monitoring and
some advanced features, such as network profiling, activity monitoring,
detailed logging and network traffic statistics with help of vnstat reporting.
""",
        packages=["net_monitor"],
        package_dir = {"net_monitor": "src"},
        scripts=["src/net_monitor"],
        ext_modules=[module1])
