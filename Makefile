PACKAGE = net_monitor
VERSION = 0.01
GITPATH = ssh://git.mandriva.com/git/projects/net_monitor.git

all: version

version:
	echo "version='$(VERSION)'" > version.py

clean:
	-find . -name '*.o' -o -name '*.py[oc]' -o -name '*~' | xargs rm -f

install: all
	mkdir -p $(RPM_BUILD_ROOT)/usr/bin/
	install -m755 net_monitor.py $(RPM_BUILD_ROOT)/usr/bin/net_monitor

cleandist:
	rm -rf $(PACKAGE)-$(VERSION) $(PACKAGE)-$(VERSION).tar.bz2

dist: gitdist

gitdist: cleandist
	git archive --prefix $(PACKAGE)-$(VERSION)/ HEAD | bzip2 -9 > $(PACKAGE)-$(VERSION).tar.bz2
