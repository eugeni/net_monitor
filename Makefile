PACKAGE = net_monitor
VERSION = 0.06
GITPATH = ssh://git.mandriva.com/git/projects/net_monitor.git

all: version python

version:
	echo "version='$(VERSION)'" > version.py

python:
	python setup.py build

clean:
	-find . -name '*.o' -o -name '*.py[oc]' -o -name '*~' | xargs rm -f

install: all
	python setup.py install --root=$(RPM_BUILD_ROOT)
	install -d /etc/sysconfig/network-scripts/ifup.d
	install -d /etc/sysconfig/network-scripts/ifdown.d
	install -m755 scripts/netmonitor_up $(RPM_BUILD_ROOT)/etc/sysconfig/network-scripts/ifup.d/
	install -m755 scripts/netmonitor_down $(RPM_BUILD_ROOT)/etc/sysconfig/network-scripts/ifdown.d/

cleandist:
	rm -rf $(PACKAGE)-$(VERSION) $(PACKAGE)-$(VERSION).tar.bz2

dist: gitdist

gitdist: cleandist
	git archive --prefix $(PACKAGE)-$(VERSION)/ HEAD | bzip2 -9 > $(PACKAGE)-$(VERSION).tar.bz2
