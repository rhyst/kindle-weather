while true; do
	cat "/dev/input/by-path/platform-zforce.0-event" | while read -n1 line; do
                break
        done
        if [ -f "mode-wifi" ]
        then
                # Switch to refresh mode
                rm "mode-wifi"
                eips 38 39 "Refresh "
                touch "mode-refresh"
        elif [ -f "mode-refresh" ]
        then
                # Switch to close mode
                rm "mode-refresh"
                eips 38 39 "Exit    "
                touch "mode-close"
        elif [ -f "mode-close" ]
        then
                # Switch to wifi mode
                rm "mode-close"
                if [ 0 -eq `lipc-get-prop com.lab126.cmd wirelessEnable` ]; then
                        eips 38 39 "WiFi Off"
                else
                        eips 38 39 "WiFi On "
                fi
                touch "mode-wifi"
        fi
        sleep 1
done