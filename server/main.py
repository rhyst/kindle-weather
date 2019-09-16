import os
import json
import requests
from flask import Flask, send_file, request, redirect, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from PIL import Image, ImageFont, ImageDraw
from astral import Astral
from dotenv import load_dotenv
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import arrow

load_dotenv()
MO_API_KEY = os.getenv('MO_API_KEY')
IMAGE_NAME = os.getenv('IMAGE_NAME')
REDIRECT_URI = os.getenv('REDIRECT_URI')
MO_LOCATION_ID = os.getenv('MO_LOCATION_ID')
ASTRAL_LOCATION = os.getenv('ASTRAL_LOCATION')
TIMEZONE = os.getenv('TIMEZONE')

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
	# Create api credentials
	credentials = None
	if os.path.exists('config/credentials.dat'):
		with open('config/credentials.dat', 'rb') as credentials_dat:
			credentials = pickle.load(credentials_dat)
	if not credentials:
		flow = Flow.from_client_secrets_file(
				'config/client_id.json',
				scopes=['https://www.googleapis.com/auth/calendar.readonly'],
				redirect_uri=REDIRECT_URI)
		code = request.args.get('code')
		if not code:
			auth_url, _ = flow.authorization_url(prompt='consent')
			return redirect(auth_url)
		flow.fetch_token(code=code)
		credentials = flow.credentials
		with open('config/credentials.dat', 'wb') as credentials_dat:
			pickle.dump(credentials, credentials_dat)
	if credentials and credentials.expired:
		credentials.refresh(Request())

	bigfont = ImageFont.truetype("fonts/Roboto.ttf", 26, encoding="unic")
	font = ImageFont.truetype("fonts/Roboto.ttf", 20, encoding="unic")
	smallfont = ImageFont.truetype("fonts/Roboto.ttf", 18, encoding="unic")
	smallerfont = ImageFont.truetype("fonts/Roboto.ttf", 12, encoding="unic")
	boldfont = ImageFont.truetype("fonts/RobotoBold.ttf", 18, encoding="unic")

	# Get forecast
	r = requests.get('http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/{}?res=3hourly&key={}'.format(MO_LOCATION_ID, MO_API_KEY))
	data = r.json()

	# Convert forecast to something readable
	hourly_predictions = []
	for day in data["SiteRep"]['DV']['Location']['Period']:
		date = day['value'][:-1]
		predictions = day['Rep']
		for prediction in predictions:
			prediction['date'] = date
			prediction['time'] = str(int(int(prediction['$']) / 60)) + ':00'
			prediction['datetime'] = date + ' ' + str(int(int(prediction['$']) / 60)) + ':00'
			hourly_predictions.append(prediction)
	
	hourly_updated_at = arrow.get(data["SiteRep"]['DV']['dataDate'])

	r = requests.get('http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/{}?res=daily&key={}'.format(MO_LOCATION_ID, MO_API_KEY))
	data = r.json()

	# Convert forecast to something readable
	daily_predictions = []
	for day in data["SiteRep"]['DV']['Location']['Period']:
		date = day['value'][:-1]
		daypred = day['Rep'][0]
		nightpred = day['Rep'][1]
		daily_predictions.append({
			"date": date,
			"Dm": daypred['Dm'],
			"Nm": nightpred['Nm'],
			"PPd": daypred['PPd'],
			"PPn": nightpred['PPn'],
			"W": daypred['W'],
			"Dd": daypred['D'],
			"Dn": nightpred['D'],
			"Gn": daypred['Gn'],
			"Gm": nightpred['Gm']
		})

	daily_updated_at = arrow.get(data["SiteRep"]['DV']['dataDate'])

	# Get todays sunrise and sunset
	now=arrow.now(TIMEZONE)
	a = Astral()
	location = a[ASTRAL_LOCATION]
	sun = location.sun(local=True, date=now)
	sunrise = sun['sunrise']
	sunset = sun['sunset']
	day_len = sunset - sunrise

	# Get yesterdays sunrise and sunset
	d_yest = now.shift(days=-1)
	sun_yest = location.sun(local=True, date=d_yest)
	sunrise_yest = sun_yest['sunrise']
	sunset_yest = sun_yest['sunset']
	day_len_yest = sunset_yest - sunrise_yest
	day_len_diff =  day_len - day_len_yest if day_len > day_len_yest else day_len_yest - day_len
	sunrise_diff =  sunrise - sunrise_yest if sunrise > sunrise_yest else sunrise_yest - sunrise
	sunset_diff = sunset - sunset_yest if sunset < sunset_yest else sunset_yest - sunset

	# Get upcoming calendar events
	calendar_sdk = build('calendar', 'v3', credentials=credentials)
	calendar_list = calendar_sdk.calendarList().list().execute()

	calendar_ids = [ calendar_list_entry['id'] for calendar_list_entry in calendar_list['items'] ]
	today = arrow.now(TIMEZONE)
	today_morning = today.strftime('%Y-%m-%dT00:00:00Z')
	tomorrow = today.shift(days=1)
	events = []
	for calendar_id in calendar_ids:
		events_page = calendar_sdk.events().list(
			calendarId=calendar_id, 
			timeMin=today_morning,
			maxResults=10,
			singleEvents=True,
			orderBy="startTime",
			).execute()
		events += events_page['items']

	def get_key(event):
		if 'dateTime' in event['start']:
			return arrow.get(event['start']['dateTime'])
		else:
			return arrow.get(event['start']['date'])
	events.sort(key=get_key)

	def calendar(draw, start_x, start_y, end_y):
		x = start_x
		y = start_y
		item_spacing = 25
		extra_day_spacing = 5
		current_date = None
		for event in events:
			if y >= end_y:
				break
			summary = event['summary']
			if 'organizer' in event and 'displayName' in event['organizer']:
				calendar = event['organizer']['displayName']
			if 'dateTime' in event['start']:
				start_time = arrow.get(event['start']['dateTime'])
				end_time = arrow.get(event['end']['dateTime'])
				diff = abs(start_time - end_time)
				time_text = start_time.strftime('%H:%M') + ' ' + str(diff.seconds//3600) + ' hours' 
			else:
				start_time = arrow.get(event['start']['date'])
				time_text = 'All day'
			if current_date != start_time.strftime('%Y/%m/%d'):
				if y + item_spacing + extra_day_spacing >= 750:
					break
				y += extra_day_spacing
				if start_time.strftime('%Y/%m/%d') == today.strftime('%Y/%m/%d'):
					text = 'Today'
				elif start_time.strftime('%Y/%m/%d') == tomorrow.strftime('%Y/%m/%d'):
					text = 'Tomorrow'
				else:
					text = start_time.humanize().capitalize() + ' on ' + start_time.format('dddd {} Do {} MMMM').format('the', 'of')
				draw.text((x, y), text, (0,0,0), boldfont)
				current_date = start_time.strftime('%Y/%m/%d')
				y += item_spacing
			text = time_text 
			draw.text((x, y), text, (0,0,0), smallfont)
			text = summary
			if len(text) > 60:
				text = text[:57] + '...'
			draw.text((x + 125, y), text, (0,0,0), smallfont)
			y += item_spacing

	def landscape():
		# Make blank image
		image_pixels = [(255, 255, 255) for i in range(800*600)]
		image = Image.new("RGBA", (800,600))
		image.putdata(image_pixels)
		draw = ImageDraw.Draw(image)

		# Big date title
		text =  now.format('dddd {} Do {} MMMM YYYY').format('the', 'of')
		w, h = bigfont.getsize(text)
		center_offset = (800 - w) / 2
		draw.text((center_offset, 5), text, (0,0,0), bigfont)

		# Render sunrise icon and todays sunrise time
		icon = Image.open('icons/sunrise.png')
		image.paste(icon, box=(10, 20), mask=icon)
		text = sunrise.strftime('%H:%M')
		w, h = bigfont.getsize(text)
		center_offset = (100 - w) / 2
		draw.text((10 + center_offset, 110), text, (0,0,0), bigfont)

		# Render sunrise diff
		text = '(+' if sunrise > sunrise_yest else '(-'
		text += ':'.join(str(sunrise_diff).split(':')[1:3]) + ')'
		w, h = smallfont.getsize(text)
		center_offset = (100 - w) / 2
		draw.text((10 + center_offset, 145), text, (0,0,0), smallfont)

		start_offset = 112
		start_height = 20
		column_width = 100
		spacing = 8
		for index, prediction in enumerate(hourly_predictions[1:6]):
			left_offset = (spacing * (index + 1)) + (index * (column_width + spacing)) + start_offset
			# Draw weather icon
			icon = Image.open('icons/' + prediction["W"] + '.png')
			image.paste(icon, box=(left_offset, start_height), mask=icon)
			# Write datetime
			text = prediction["time"]
			w, h = bigfont.getsize(text)
			center_offset = (100 - w) / 2
			draw.text((left_offset + center_offset, start_height + 90), text, (0,0,0), bigfont)
			# Write temperature
			icon = Image.open('icons/small/thermometer.png')
			image.paste(icon, box=(left_offset, start_height + 120), mask=icon)
			text = prediction["F"] + '°C'
			w, h = font.getsize(text)
			center_offset = (100 - w) / 2
			draw.text((left_offset + center_offset, start_height + 120), text, (0,0,0), font)
			# Write rain chance
			icon = Image.open('icons/small/rain.png')
			image.paste(icon, box=(left_offset, start_height + 145), mask=icon)		
			text = prediction["Pp"] + '%'
			w, h = font.getsize(text)
			center_offset = (100 - w) / 2
			draw.text((left_offset + center_offset, start_height + 145), text, (0,0,0), font)
			# Write wind
			icon = Image.open('icons/small/deg-' + prediction['D'] + '.png')
			image.paste(icon, box=(left_offset, start_height + 175), mask=icon)		
			text = str(int(1.609344 * float(prediction["S"]))) + "kph"
			w, h = smallfont.getsize(text)
			center_offset = (100 - w) / 2
			draw.text((left_offset + center_offset, start_height + 175), text, (0,0,0), smallfont)
		# Render sunset icon and todays sunset time
		icon = Image.open('icons/sunset.png')
		image.paste(icon, box=(680, 20), mask=icon)
		text = sunset.strftime('%H:%M')
		w, h = bigfont.getsize(text)
		center_offset = (100 - w) / 2
		draw.text((680 + center_offset, 110), text, (0,0,0), bigfont)

		# Render sunset diff
		text = '(+' if sunset < sunset_yest else '(-'
		text += ':'.join(str(sunset_diff).split(':')[1:3]) + ')'
		w, h = smallfont.getsize(text)
		center_offset = (100 - w) / 2
		draw.text((680 + center_offset, 145), text, (0,0,0), smallfont)
				
		# Hourly updated
		text = 'Updated ' + hourly_updated_at.format('ddd h a')
		draw.text((5, 215), text, (0,0,0), smallerfont)

				# Horizontal Line
		draw.line((0, 230, 800, 230), fill=255)

		# 4 day forecast
		start_height = 230
		spacing = 10
		row_height = 70
		for index, prediction in enumerate(daily_predictions[1:6]):
			top_offset = (spacing * (index + 1)) + (index * (row_height + spacing)) + start_height
			# Write datetime
			text = arrow.get(prediction["date"]).format('dddd {} Do {} MMMM YYYY').format('the', 'of')
			draw.text((5, top_offset), text, (0,0,0), smallfont)
			# Draw weather icon
			icon = Image.open('icons/med/' + prediction["W"] + '.png')
			image.paste(icon, box=(0, top_offset + 25), mask=icon)
			# Write day
			draw.text((70, top_offset + 25), "Day", (0,0,0), smallfont)
			# Write night
			draw.text((70, top_offset + 50), "Night", (0,0,0), smallfont)		
			# Write max temperature
			icon = Image.open('icons/small/thermometer.png')
			image.paste(icon, box=(120, top_offset + 25), mask=icon)
			text = prediction["Dm"] + '°C'
			draw.text((150, top_offset + 25), text, (0,0,0), smallfont)
			# Write min temperature
			icon = Image.open('icons/small/thermometer.png')
			image.paste(icon, box=(120, top_offset + 50), mask=icon)
			text = prediction["Nm"] + '°C'
			draw.text((150, top_offset + 50), text, (0,0,0), smallfont)
			# Write day rain chance
			icon = Image.open('icons/small/rain.png')
			image.paste(icon, box=(200, top_offset + 25), mask=icon)
			text = prediction["PPd"] + '%'
			draw.text((230, top_offset + 25), text, (0,0,0), smallfont)
			# Write night rain chance
			icon = Image.open('icons/small/rain.png')
			image.paste(icon, box=(200, top_offset + 50), mask=icon)
			text = prediction["PPn"] + '%'
			draw.text((230, top_offset + 50), text, (0,0,0), smallfont)
			# Write day wind
			icon = Image.open('icons/small/deg-' + prediction['Dd'] + '.png')
			image.paste(icon, box=(280, top_offset + 25), mask=icon)
			text = str(int(1.609344 * float(prediction["Gn"]))) + "kph"
			draw.text((310, top_offset + 25), text, (0,0,0), smallfont)
			# Write night wind
			icon = Image.open('icons/small/deg-' + prediction['Dn'] + '.png')
			image.paste(icon, box=(280, top_offset + 50), mask=icon)
			text = str(int(1.609344 * float(prediction["Gm"]))) + "kph"
			draw.text((310, top_offset + 50), text, (0,0,0), smallfont)

		# Vertical Line
		draw.line((400, 230, 400, 600), fill=255)

		# Calendar
		calendar(draw, 420, 235, 550)

		# Daily updated
		text = 'Updated ' + daily_updated_at.format('ddd h a')
		draw.text((5, 585), text, (0,0,0), smallerfont)

		# Calendar and General checked at
		text = 'Updated ' + now.format('ddd h a')
		draw.text((420, 585), text, (0,0,0), smallerfont)



		image = image.rotate(-90, expand=True)

		image.save(IMAGE_NAME, "PNG")


	def portrait():
		# Make blank image
		image_pixels = [(255, 255, 255) for i in range(600*800)]
		image = Image.new("RGBA", (600,800))
		image.putdata(image_pixels)
		draw = ImageDraw.Draw(image)

		for index, prediction in enumerate(hourly_predictions[1:6]):
			left_offset = (10 * (index + 1)) + (index * 110)
			# Draw weather icon
			icon = Image.open('icons/' + prediction["W"] + '.png')
			image.paste(icon, box=(left_offset, 0), mask=icon)
			# Write datetime
			text = prediction["time"]
			w, h = bigfont.getsize(text)
			center_offset = (100 - w) / 2
			draw.text((left_offset + center_offset, 90), text, (0,0,0), bigfont)
			# Write temperature
			icon = Image.open('icons/small/thermometer.png')
			image.paste(icon, box=(left_offset, 120), mask=icon)
			text = prediction["F"] + '°C'
			w, h = font.getsize(text)
			center_offset = (100 - w) / 2
			draw.text((left_offset + center_offset, 120), text, (0,0,0), font)
			# Write rain chance
			icon = Image.open('icons/small/rain.png')
			image.paste(icon, box=(left_offset, 145), mask=icon)		
			text = prediction["Pp"] + '%'
			w, h = font.getsize(text)
			center_offset = (100 - w) / 2
			draw.text((left_offset + center_offset, 145), text, (0,0,0), font)
			# Write wind
			icon = Image.open('icons/small/deg-' + prediction['D'] + '.png')
			image.paste(icon, box=(left_offset, 175), mask=icon)		
			text = str(int(1.609344 * float(prediction["S"]))) + "kph"
			w, h = smallfont.getsize(text)
			center_offset = (100 - w) / 2
			draw.text((left_offset + center_offset, 175), text, (0,0,0), smallfont)

		# Render sunrise icon and todays sunrise time
		icon = Image.open('icons/sunrise.png')
		image.paste(icon, box=(130, 200), mask=icon)
		text = sunrise.strftime('%H:%M')
		w, h = bigfont.getsize(text)
		center_offset = (100 - w) / 2
		draw.text((130 + center_offset, 290), text, (0,0,0), bigfont)

		# Render sun icon, day length and day length diff from yesterday
		icon = Image.open('icons/1.png')
		image.paste(icon, box=(250, 200), mask=icon)
		text = ':'.join(str(day_len).split(':')[:2])
		w, h = bigfont.getsize(text)
		center_offset = (100 - w) / 2
		draw.text((250 + center_offset, 290), text, (0,0,0), bigfont)

		text = '(+' if day_len > day_len_yest else '(-'
		text += ':'.join(str(day_len_diff).split(':')[1:3]) + ')'
		w, h = smallfont.getsize(text)
		center_offset = (100 - w) / 2
		draw.text((250 + center_offset, 320), text, (0,0,0), smallfont)

		# Render sunset icon and todays sunset time
		icon = Image.open('icons/sunset.png')
		image.paste(icon, box=(370, 200), mask=icon)
		text = sunset.strftime('%H:%M')
		w, h = bigfont.getsize(text)
		center_offset = (100 - w) / 2
		draw.text((370 + center_offset, 290), text, (0,0,0), bigfont)

		# Write checked time and updated time
		text = 'Checked at ' + now.format('ddd h a') + ' and last updated at ' + hourly_updated_at.format('ddd h a')
		draw.text((10, 775), text, (0,0,0), smallfont)

		draw.line((0, 345, 600, 345), fill=255)
		text =  now.format('dddd {} Do {} MMMM YYYY').format('the', 'of')
		w, h = bigfont.getsize(text)
		center_offset = (600 - w) / 2
		draw.text((center_offset, 350), text, (0,0,0), bigfont)

		calendar(draw, 10, 380, 750)

		image.save(IMAGE_NAME, "PNG")

	landscape() if request.args.get('landscape') is not None else portrait()

	return send_file(IMAGE_NAME, as_attachment=False)

@app.route('/config')
def config():
	if os.path.exists('config/config.json'):
		with open('config/config.json', 'r') as config:
			return jsonify(json.load(config))
	return ""
