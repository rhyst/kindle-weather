cd "$(dirname "$0")"

if [ ! -f "enable" ]
then
    	echo "Not enabled"
        exit 0
fi

source ".env"

echo "Running"
DISABLE_WIFI=0
# Enable wireless if it is currently off
if [ 0 -eq `lipc-get-prop com.lab126.cmd wirelessEnable` ]; then
        echo "Enabling WiFi"
        lipc-set-prop com.lab126.cmd wirelessEnable 1
        DISABLE_WIFI=1
        sleep 60
fi

echo "Getting image"
rm ss.png
curl -L --user $USER:$PASSWORD $URL > ss.png

echo "Processing image"
./convert ss.png -filter LanczosSharp -resize 600x800 -background black -gravity center -extent 600x800 -colorspace Gray -dither FloydSteinberg -remap kindle_colors.gif -quality 75 -define png:color-type=0 -def$

echo "Displaying image"
eips -fg ss.png
eips 47 39 "$(gasgauge-info -s)"

# Disable wireless if necessary
if [ 1 -eq $DISABLE_WIFI ]; then
        echo "Disabling WiFi"
        lipc-set-prop com.lab126.cmd wirelessEnable 0
fi

if [ 0 -eq `lipc-get-prop com.lab126.cmd wirelessEnable` ]; then
        eips 38 39 "WiFi Off"
else
        eips 38 39 "WiFi On "
fi
