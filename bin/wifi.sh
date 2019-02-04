while true; do
	cat "/dev/input/by-path/platform-zforce.0-event" | while read -n1 line; do
                break
        done

	if [ 0 -eq `lipc-get-prop com.lab126.cmd wirelessEnable` ]; then
                lipc-set-prop com.lab126.cmd wirelessEnable 1
                eips 38 39 "WiFi On "
        else
            	lipc-set-prop com.lab126.cmd wirelessEnable 0
                eips 38 39 "WiFi Off"
        fi
done