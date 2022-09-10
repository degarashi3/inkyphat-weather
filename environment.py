#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import glob
import os
import time
import json
import subprocess
from subprocess import PIPE
from sys import exit
from collections import OrderedDict
from font_fredoka_one import FredokaOne
from inky.auto import auto
from PIL import Image, ImageDraw, ImageFont

"""
To run this example on Python 2.x you should:
    sudo apt install python-lxml
    sudo pip install geocoder requests font-fredoka-one beautifulsoup4=4.6.3

On Python 3.x:
    sudo apt install python3-lxml
    sudo pip3 install geocoder requests font-fredoka-one beautifulsoup4
"""

try:
    import requests
except ImportError:
    exit("This script requires the requests module\nInstall with: sudo pip install requests")

try:
    import geocoder
except ImportError:
    exit("This script requires the geocoder module\nInstall with: sudo pip install geocoder")

try:
    from bs4 import BeautifulSoup
except ImportError:
    exit("This script requires the bs4 module\nInstall with: sudo pip install beautifulsoup4==4.6.3")

# Get the current path
PATH = os.path.dirname(__file__)

# Set up the display
try:
    inky_display = auto(ask_user=True, verbose=True)
except TypeError:
    raise TypeError("You need to update the Inky library to >= v1.1.0")

if inky_display.resolution not in ((212, 104), (250, 122)):
    w, h = inky_display.resolution
    raise RuntimeError("This example does not support {}x{}".format(w, h))

inky_display.set_border(inky_display.BLACK)

# Details to customise your weather display

CITY = "Shibuya"
COUNTRYCODE = "JP"
WARNING_TEMP = 30.0


# Convert a city name and country code to latitude and longitude
def get_coords(address):
    g = geocoder.arcgis(address)
    coords = g.latlng
    return coords


# Query Dark Sky (https://darksky.net/) to scrape current weather data
def get_weather(address):
    coords = get_coords(address)
    weather = {}
    res = requests.get("https://darksky.net/forecast/{}/uk212/en".format(",".join([str(c) for c in coords])))
    if res.status_code == 200:
        soup = BeautifulSoup(res.content, "lxml")
        curr = soup.find_all("span", "currently")
        weather["summary"] = curr[0].img["alt"].split()[0]
        press = soup.find_all("div", "pressure")
        weather["pressure"] = int(press[0].find("span", "num").text)

        url = 'https://api.nature.global/1/devices'
        payload = {'accept':'application/json'}
        headers = {'Authorization':'Bearer EFJnSt9QxpTXS-6Cjje6tek8XcrgtIJyryGoUTzmOXQ.Bm-5558aXH9au-77xT-RiKGeeM7PD9IeQ2-q4bTuhBU'}
        r = requests.get(url, data=payload, headers=headers)
        
        d = json.loads(r.text)
        
        weather["temperature"] = float(d[0]['newest_events']['te']['val'])
        weather["humidity"] = int(d[0]['newest_events']['hu']['val'])
        
        co2 = subprocess.run('ssh pi@watcher.local sudo python -m mh_z19', shell=True, stdout=PIPE, stderr=PIPE, text=True)
        ret = json.loads(co2.stdout)
        weather["co2"] = int(ret['co2'])

        return weather
    else:
        return weather


def create_mask(source, mask=(inky_display.WHITE, inky_display.BLACK, inky_display.RED)):
    """Create a transparency mask.

    Takes a paletized source image and converts it into a mask
    permitting all the colours supported by Inky pHAT (0, 1, 2)
    or an optional list of allowed colours.

    :param mask: Optional list of Inky pHAT colours to allow.

    """
    mask_image = Image.new("1", source.size)
    w, h = source.size
    for x in range(w):
        for y in range(h):
            p = source.getpixel((x, y))
            if p in mask:
                mask_image.putpixel((x, y), 255)

    return mask_image


# Dictionaries to store our icons and icon masks in
icons = {}
masks = {}

# Get the weather data for the given location
location_string = "{city}, {countrycode}".format(city=CITY, countrycode=COUNTRYCODE)
weather = get_weather(location_string)

# This maps the weather summary from Dark Sky
# to the appropriate weather icons
icon_map = {
    "snow": ["snow", "sleet"],
    "rain": ["rain"],
    "cloud": ["fog", "cloudy", "partly-cloudy-day", "partly-cloudy-night"],
    "sun": ["clear-day", "clear-night"],
    "storm": [],
    "wind": ["wind"]
}

# Placeholder variables
pressure = 0
temperature = 0
co2 = 0
humidity = 0
weather_icon = None

if weather:
    temperature = weather["temperature"]
    humidity = weather["humidity"]
    co2 = weather["co2"]
    pressure = weather["pressure"]
    summary = weather["summary"]

    for icon in icon_map:
        if summary in icon_map[icon]:
            weather_icon = icon
            break

else:
    print("Warning, no weather information found!")

# Create a new canvas to draw on
# img = Image.open(os.path.join(PATH, "resources/simple.png")).resize(inky_display.resolution)
bg = ""
if co2 > 1000:
    bg = "resources/warning.png"

else:
    bg = "resources/simple.png"

img = Image.open(os.path.join(PATH, bg)).resize(inky_display.resolution)
draw = ImageDraw.Draw(img)

# Load our icon files and generate masks
for icon in glob.glob(os.path.join(PATH, "resources/icon-*.png")):
    icon_name = icon.split("icon-")[1].replace(".png", "")
    icon_image = Image.open(icon)
    icons[icon_name] = icon_image
    masks[icon_name] = create_mask(icon_image)

# Load the FredokaOne font

# font = ImageFont.truetype(FredokaOne, 22)
font = ImageFont.truetype("NotoSansMono-Regular.ttf", 20)
font_ja = ImageFont.truetype("NotoSansCJK-Regular.ttc", 20)

# Draw lines to frame the weather data
draw.line((52, 36, 52, 83))       # Vertical line
draw.line((14, 35, 240, 35))      # Horizontal top line
draw.line((57, 58, 240, 58))      # Horizontal middle line
draw.line((14, 83, 240, 83))      # Horizontal bottom line
# draw.line((169, 58, 169, 58), 2)  # Red seaweed pixel :D

# Write text with weather values to the canvas
datetime = time.strftime("%Y/%m/%d %a")

draw.text((19, 10), datetime, inky_display.WHITE, font=font)

# draw.text((72, 34), "T", inky_display.WHITE, font=font)
# draw.text((92, 34), u"{}°C".format(temperature), inky_display.WHITE if temperature < WARNING_TEMP else inky_display.RED, font=font)
draw.text((55, 34), "T:" + u"{}°C".format(temperature) + "  H:" +  u"{}%".format(humidity), inky_display.WHITE, font=font)

# draw.text((72, 58), "CO2", inky_display.WHITE, font=font)
# draw.text((122, 58), u"{}ppm".format(co2), inky_display.WHITE, font=font)
draw.text((55, 57), "CO2:" + u"{}ppm".format(co2), inky_display.WHITE if co2 < 1000 else inky_display.RED, font=font)

if co2 > 1000:
    draw.text((19, 81), "今すぐ換気しろ", inky_display.RED, font=font_ja)

else:
    draw.text((19, 81), "平常", inky_display.WHITE, font=font_ja)
    

# Draw the current weather icon over the backdrop
if weather_icon is not None:
    img.paste(icons[weather_icon], (11, 36), masks[weather_icon])

else:
    draw.text((11, 36), "?", inky_display.RED, font=font)

# Display the weather data on Inky pHAT
inky_display.set_image(img)
inky_display.show()
