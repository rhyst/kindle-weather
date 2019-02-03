import os
import json
import requests
import datetime
from flask import Flask, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from PIL import Image, ImageFont, ImageDraw
from astral import Astral
from dotenv import load_dotenv
import pickle
from datetime import timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import arrow

load_dotenv()
MO_API_KEY = os.getenv('MO_API_KEY')
IMAGE_NAME = os.getenv('IMAGE_NAME')


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
	SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', ]
	if not os.path.exists('config/credentials.dat'):
		flow = InstalledAppFlow.from_client_secrets_file('config/client_id.json', SCOPES)
		credentials = flow.run_local_server()
		with open('config/credentials.dat', 'wb') as credentials_dat:
			pickle.dump(credentials, credentials_dat)
	else:
		with open('config/credentials.dat', 'rb') as credentials_dat:
			credentials = pickle.load(credentials_dat)

	if credentials.expired:
		credentials.refresh(Request())
	
	# Make blank image
	image_pixels = [(255, 255, 255) for i in range(600*800)]
	image = Image.new("RGBA", (600,800))
	image.putdata(image_pixels)
	draw = ImageDraw.Draw(image)

	bigfont = ImageFont.truetype("Roboto.ttf", 26, encoding="unic")
	font = ImageFont.truetype("Roboto.ttf", 20, encoding="unic")
	smallfont = ImageFont.truetype("Roboto.ttf", 18, encoding="unic")
	boldfont = ImageFont.truetype("RobotoBold.ttf", 18, encoding="unic")

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
		text = prediction["time"]
		w, h = bigfont.getsize(text)
		center_offset = (100 - w) / 2
		draw.text((left_offset + center_offset, 85), text, (0,0,0), bigfont)
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

	d = datetime.datetime.now()
	a = Astral()
	location = a['London']
	sun = location.sun(local=True, date=d)
	sunrise = sun['sunrise']
	sunset = sun['sunset']

	icon = Image.open('icons/sunrise.png')
	image.paste(icon, box=(130, 200), mask=icon)
	text = sunrise.strftime('%H:%M')
	w, h = bigfont.getsize(text)
	center_offset = (100 - w) / 2
	draw.text((130 + center_offset, 290), text, (0,0,0), bigfont)

	icon = Image.open('icons/sunset.png')
	image.paste(icon, box=(370, 200), mask=icon)
	text = sunset.strftime('%H:%M')
	w, h = bigfont.getsize(text)
	center_offset = (100 - w) / 2
	draw.text((370 + center_offset, 290), text, (0,0,0), bigfont)

	# Write checked time and updated time
	updated_at = datetime.datetime.strptime(data["SiteRep"]['DV']['dataDate'],"%Y-%m-%dT%H:%M:00Z")
	text = 'Checked at ' + d.strftime('%H:%M') + ' and last updated at ' + updated_at.strftime('%H:%M')
	draw.text((10, 775), text, (0,0,0), smallfont)

	# Get upcoming calendar events
	calendar_sdk = build('calendar', 'v3', credentials=credentials)
	calendar_list = calendar_sdk.calendarList().list().execute()
	for calendar in calendar_list['items']:
		print(calendar['id'] + ' ' + calendar['summary'])
	calendar_ids = [ calendar_list_entry['id'] for calendar_list_entry in calendar_list['items'] ]
	today = datetime.datetime.now()
	today_morning = today.strftime('%Y-%m-%dT00:00:00Z')
	tomorrow = today + timedelta(days=1)
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

	def suffix(d):
		return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')
	def custom_strftime(format, t):
		return t.strftime(format).replace('{S}', str(t.day) + suffix(t.day))
	draw.line((0, 330, 600, 330), fill=255)
	text = 	custom_strftime('%A the {S} of %B %Y', d)
	w, h = bigfont.getsize(text)
	center_offset = (600 - w) / 2
	draw.text((center_offset, 340), text, (0,0,0), bigfont)
	y = 370

	def get_key(event):
		if 'dateTime' in event['start']:
			return datetime.datetime.strptime(event['start']['dateTime'], '%Y-%m-%dT%H:%M:%SZ')
		else:
			return datetime.datetime.strptime(event['start']['date'], '%Y-%m-%d')
	events.sort(key=get_key)

	item_spacing = 25
	extra_day_spacing = 5
	current_date = None
	for event in events:
		if y >= 750:
			break
		summary = event['summary']
		calendar = 'Unknown'
		if 'organizer' in event and 'displayName' in event['organizer']:
			calendar = event['organizer']['displayName']
		if 'dateTime' in event['start']:
			start_time = datetime.datetime.strptime(event['start']['dateTime'], '%Y-%m-%dT%H:%M:%SZ')
			end_time = datetime.datetime.strptime(event['end']['dateTime'], '%Y-%m-%dT%H:%M:%SZ')
			diff = abs(start_time - end_time)
			time_text = start_time.strftime('%H:%M') + ' ' + str(diff.seconds//3600) + ' hours' 
		else:
			start_time = datetime.datetime.strptime(event['start']['date'], '%Y-%m-%d')
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
				text = arrow.get(start_time).humanize().capitalize() + ' on ' + custom_strftime('%A the {S} of %B', start_time)
			draw.text((10, y), text, (0,0,0), boldfont)
			current_date = start_time.strftime('%Y/%m/%d')
			y += item_spacing
		text = time_text 
		draw.text((10, y), text, (0,0,0), smallfont)
		text = summary
		if len(text) > 60:
			text = text[:57] + '...'
		draw.text((135, y), text, (0,0,0), smallfont)
		y += item_spacing

	image.save(IMAGE_NAME, "PNG")

	return send_file(IMAGE_NAME, as_attachment=False)
