while true; do
        cat "/dev/input/by-path/platform-whitney-button-event" | while read -n1 line; do
                break 
        done
        if [ -f "mode-wifi" ]
        then
                if [ 0 -eq `lipc-get-prop com.lab126.cmd wirelessEnable` ]; then
                        eips 38 39 "WiFi On "
                        lipc-set-prop com.lab126.cmd wirelessEnable 1
                else
                        eips 38 39 "WiFi Off"
                        lipc-set-prop com.lab126.cmd wirelessEnable 0
                fi
        elif [ -f "mode-refresh" ]
        then
                ./display-weather.sh
        elif [ -f "mode-close" ]
        then
                for id in $(ps aux | grep monitor-wifi.sh | awk '{print $2}'); do
                        kill -9 $id
                done
                rm "enable"
                rm "mode-refresh"
                rm "mode-close"
                rm "mode-wifi"
                lipc-set-prop com.lab126.cmd wirelessEnable 1
                start lab126_gui
                exit 0
        fi
        sleep 1
done