cat "/dev/input/by-path/platform-whitney-button-event" | while read -n1 line; do
	break 
done
for id in $(ps aux | grep wifi.sh | awk '{print $2}'); do
        kill -9 $id
done
rm enable
lipc-set-prop com.lab126.cmd wirelessEnable 1
start lab126_gui
