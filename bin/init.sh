cd "$(dirname "$0")"

echo "Disabling framework"
stop lab126_gui
sleep 5
eips -d l=fff,w=600,h=800

eips 13 16 "WeatherCalc is loading...""
echo "Setting enable flag"
touch enable

echo "Turning off power saving"
lipc-set-prop com.lab126.powerd preventScreenSaver 1

echo "Fetching and displaying information"
./display-weather.sh

echo "Listening for key press"
for id in $(ps aux | grep monitor.sh | awk '{print $2}'); do
	kill -9 $id
done
./monitor.sh &

echo "Listening for screen tap"
for id in $(ps aux | grep monitor.sh | awk '{print $2}'); do
	kill -9 $id
done
./wifi.sh