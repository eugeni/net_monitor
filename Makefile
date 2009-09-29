PACKAGE = net_monitor
VERSION = 0.01
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

cleandist:
	rm -rf $(PACKAGE)-$(VERSION) $(PACKAGE)-$(VERSION).tar.bz2

dist: gitdist

gitdist: cleandist
	git archive --prefix $(PACKAGE)-$(VERSION)/ HEAD | bzip2 -9 > $(PACKAGE)-$(VERSION).tar.bz2
