all: plasmapkg

plasmapkg:
	zip -r ../../net_monitor_plasma.zip contents/ metadata.desktop

clean:
	rm -f ../../net_monitor_plasma.zip

test: clean plasmapkg
	plasmapkg -t plasmoid -r net_monitor
	plasmapkg -t plasmoid -i ../../net_monitor_plasma.zip
