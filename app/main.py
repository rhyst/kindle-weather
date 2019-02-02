import json
from PIL import Image, ImageFont, ImageDraw
import requests
from flask import Flask, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import datetime
from astral import Astral
from dotenv import load_dotenv

load_dotenv()
MO_API_KEY = os.get('MO_API_KEY')
IMAGE_NAME = os.get('IMAGE_NAME')


WEATHER_TYPES = {
	"NA": "Not available",
	"0": "Clear night",
	"1": "Sunny day",
	"2": "Partly cloudy (night)",
	"3": "Partly cloudy (day)",
	"4": "Not used",
	"5": "Mist",
	"6": "Fog",
	"7": "Cloudy",
	"8": "Overcast",
	"9": "Light rain shower (night)",
	"10": "Light rain shower (day)",
	"11": "Drizzle",
	"12": "Light rain",
	"13": "Heavy rain shower (night)",
	"14": "Heavy rain shower (day)",
	"15": "Heavy rain",
	"16": "Sleet shower (night)",
	"17": "Sleet shower (day)",
	"18": "Sleet",
	"19": "Hail shower (night)",
	"20": "Hail shower (day)",
	"21": "Hail",
	"22": "Light snow shower (night)",
	"23": "Light snow shower (day)",
	"24": "Light snow",
	"25": "Heavy snow shower (night)",
	"26": "Heavy snow shower (day)",
	"27": "Heavy snow",
	"28": "Thunder shower (night)",
	"29": "Thunder shower (day)",
	"30": "Thunder"
}

app = Flask(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["5/minute"]
)

@app.route("/")
def main():
	# Make blank image
	image_pixels = [(255, 255, 255) for i in range(600*800)]
	image = Image.new("RGBA", (600,800))
	image.putdata(image_pixels)
	draw = ImageDraw.Draw(image)

	# Get forecast
	r = requests.get('http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/351526?res=3hourly&key=' + MO_API_KEY)
	data = r.json()

	# Convert forecast to something readable
	field_key = { a['name']: {'name': a['$'], 'units': a['units']} for a in data["SiteRep"]['Wx']['Param'] }
	all_predictions = []
	for day in data["SiteRep"]['DV']['Location']['Period']:
		date = day['value'][:-1]
		predictions = day['Rep']
		for prediction in predictions:
			prediction['date'] = date
			prediction['time'] = str(int(int(prediction['$']) / 60)) + ':00'
			prediction['datetime'] = date + ' ' + str(int(int(prediction['$']) / 60)) + ':00'
			all_predictions.append(prediction)
	update_time = data["SiteRep"]['DV']['dataDate']
	forecast = ''
	for index, prediction in enumerate(all_predictions[1:6]):
		left_offset = (10 * (index + 1)) + (index * 110)
		# Draw weather icon
		icon = Image.open('icons/' + prediction["W"] + '.png')
		image.paste(icon, box=(left_offset, 0), mask=icon)
		# Write datetime
		text = prediction["datetime"]
		w, h = draw.textsize(text)
		center_offset = (100 - w) / 2
		draw.text((left_offset + center_offset, 100), text, (0,0,0))
		# Write weather type
		text = WEATHER_TYPES[prediction["W"]]
		w, h = draw.textsize(text)
		center_offset = (100 - w) / 2
		draw.text((left_offset + center_offset, 115), text, (0,0,0))
		# Write temperature
		text = 'Feels like ' + prediction["F"] + ' °C'
		w, h = draw.textsize(text)
		center_offset = (100 - w) / 2
		draw.text((left_offset + center_offset, 130), text, (0,0,0))
		# Write rain chance
		text = prediction["Pp"] + '% chance of rain'
		w, h = draw.textsize(text)
		center_offset = (100 - w) / 2
		draw.text((left_offset + center_offset, 145), text, (0,0,0))

	d = datetime.datetime.now()
	a = Astral()
	location = a['London']
	sun = location.sun(local=True, date=d)
	sunrise = sun['sunrise']
	sunset = sun['sunset']

	icon = Image.open('icons/sunrise.png')
	image.paste(icon, box=(130, 160), mask=icon)
	text = sunrise.strftime('%H:%M')
	w, h = draw.textsize(text)
	center_offset = (100 - w) / 2
	draw.text((130 + center_offset, 260), text, (0,0,0))

	icon = Image.open('icons/sunset.png')
	image.paste(icon, box=(370, 160), mask=icon)
	text = sunset.strftime('%H:%M')
	w, h = draw.textsize(text)
	center_offset = (100 - w) / 2
	draw.text((370 + center_offset, 260), text, (0,0,0))

	# Write checked time and updated time
	updated_at = datetime.datetime.strptime(data["SiteRep"]['DV']['dataDate'],"%Y-%m-%dT%H:%M:00Z")
	text = 'Checked at ' + d.strftime('%H:%M') + ' and last updated at ' + updated_at.strftime('%H:%M')
	w, h = draw.textsize(text)
	draw.text((10, 790), text, (0,0,0))

	image.save(IMAGE_NAME, "PNG")

	return send_file(IMAGE_NAME, as_attachment=False)
