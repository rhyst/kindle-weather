cd "$(dirname "$0")"

if [ ! -f "enable" ]
then
	echo "Not enabled"
	exit 0
fi

source ".env"

echo "Running"
echo "Enabling WiFi"
DISABLE_WIFI=0
# Enable wireless if it is currently off
if [ 0 -eq `lipc-get-prop com.lab126.cmd wirelessEnable` ]; then
	logger "WiFi is off, turning it on now"
	lipc-set-prop com.lab126.cmd wirelessEnable 1
	DISABLE_WIFI=1
fi

echo "Configuring kindle settings"
lipc-set-prop com.lab126.powerd preventScreenSaver 1
lipc-set-prop com.lab126.pillow interrogatePillow '{"pillowId": "default_status_bar", "function": "nativeBridge.hideMe();"}'

echo "Getting image"
rm ss.png
wget --http-user=$USER --http-password=$PASSWORD -O ss.png $URL

echo "Processing image"
./convert ss.png -filter LanczosSharp -resize 600x800 -background black -gravity center -extent 600x800 -colorspace Gray -dither FloydSteinberg -remap kindle_colors.gif -quality 75 -define png:color-type=0 -define png:bit-depth=8 ss.png

echo "Displaying image"
eips -fg ss.png
eips 47 39 "$(gasgauge-info -s)"

# Disable wireless if necessary
if [ 1 -eq $DISABLE_WIFI ]; then
	echo "Disabling WiFi"
	lipc-set-prop com.lab126.cmd wirelessEnable 0
fi