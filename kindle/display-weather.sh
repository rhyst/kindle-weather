cd "$(dirname "$0")"

if [ ! -f "enable" ]
then
	echo "Not enabled"
	exit 0
fi

echo "Running"
lipc-set-prop com.lab126.powerd preventScreenSaver 1
lipc-set-prop com.lab126.pillow interrogatePillow '{"pillowId": "default_status_bar", "function": "nativeBridge.hideMe();"}'

echo "Getting image"
rm ss.png
wget -O ss.png http://weather.tyers.io

echo "Processing image"
./convert ss.png -filter LanczosSharp -resize 600x800 -background black -gravity center -extent 600x800 -colorspace Gray -dither FloydSteinberg -remap kindle_colors.gif -quality 75 -define png:color-type=0 -define png:bit-depth=8 ss.png

echo "Displaying image"
eips -fg ss.png
eips 47 39 "$(gasgauge-info -s)"
