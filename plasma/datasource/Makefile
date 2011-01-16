all: plasmapkg

plasmapkg:
	zip -r ../../net_monitor_data.zip contents/ metadata.desktop

clean:
	rm -f ../../net_monitor_plasma_data.zip

test: clean plasmapkg
	plasmapkg -t dataengine -r net_monitor_data
	plasmapkg -t dataengine -i ../../net_monitor_data.zip
