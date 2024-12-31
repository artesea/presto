from presto import Presto
from picovector import ANTIALIAS_BEST, PicoVector, Polygon, Transform
from machine import PWM, Pin

import datetime
import time
import re
import math
import ntptime
import requests
import plasma

# Setup for the Presto display
presto = Presto(ambient_light=False, full_res=True)
display = presto.display
WIDTH, HEIGHT = display.get_bounds()
MARGIN = 15
first_run = True
backlight = 5
presto.set_backlight(backlight/10)

# Sound Output (PWM pin)
BUZZER_PIN = 43  # Use GPIO43 for the piezo buzzer
pwm = PWM(Pin(BUZZER_PIN))

# We'll need this for the touch element of the screen
touch = presto.touch

# Plasma lights on rear
NUM_LEDS = 7
LED_PIN = 33
lights = plasma.WS2812(NUM_LEDS, 0, 0, LED_PIN)
lights.start()

# Couple of colours for use later
WHITE = display.create_pen(200, 200, 200)
GREY = display.create_pen(64, 64, 64)
DARKGREY = display.create_pen(32, 32, 32)
BLACK = display.create_pen(0, 0, 0)
BLUE = display.create_pen(0, 0, 220)
GREEN = display.create_pen(0, 128, 0)
YELLOW = display.create_pen(128, 128, 0)
ORANGE = display.create_pen(128, 80, 0)
RED = display.create_pen(128, 0, 0)

# Pico Vector
vector = PicoVector(display)
vector.set_antialiasing(ANTIALIAS_BEST)

t = Transform()
vector.set_font("Roboto-Medium.af", 24)
vector.set_font_letter_spacing(100)
vector.set_font_word_spacing(100)
vector.set_transform(t)

display.set_pen(BLACK)
display.clear()
display.set_pen(DARKGREY)
vector.text("Starting up", MARGIN, 30)
presto.update()

# Connect to Wifi
connection_successful = presto.connect()
print(connection_successful)
display.set_pen(DARKGREY)
vector.text("WiFi Connected", MARGIN, 50)
presto.update()


# Set the correct time using the NTP service.
try:
    ntptime.settime()
    display.set_pen(DARKGREY)
    vector.text("NTP done", MARGIN, 70)
    presto.update()
except OSError as e:
    print("ntp issue", e)
    display.set_pen(RED)
    vector.text("NTP issue", MARGIN, 70)
    presto.update()

def pricing_colour(price):
    ret = WHITE
    if price <= 0:
        ret = BLUE
    elif price <= 10:
        ret = GREEN
    elif price <= 23:
        ret = YELLOW
    elif price <= 30:
        ret = ORANGE
    else:
        ret = RED
    return ret

def get_pricing():
    print("Fetching Octopus Agile Prices")
    #Visit https://octopus.energy/dashboard/new/accounts/personal-details/api-access to confirm the URL for your regions Agile prices
    endpoint = "https://api.octopus.energy/v1/products/AGILE-FLEX-22-11-25/electricity-tariffs/E-1R-AGILE-FLEX-22-11-25-B/standard-unit-rates/"
    try:
        request = requests.get(endpoint)
        json = request.json()
        print("Data Received")
        if first_run:
            display.set_pen(DARKGREY)
            vector.text("Agile prices fetched", MARGIN, 90)
            presto.update()
    except OSError as e:
        print("ERROR", e)
        json = {}
    return json

def iso_parsing(isotime):
    from_matches = re.match("(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)Z", isotime)
    year,month,day,hour,minute,second = from_matches.groups()
    from_dt = datetime.datetime(int(year),int(month),int(day),int(hour),int(minute),int(second))
    return from_dt

def draw_pricing_chart(json):
    #this doesn't account for BST
    print("START: draw_pricing_chart")
    current_price = 0
    prev_price = 0
    next_price = 0
    display.set_pen(BLACK)
    display.clear()
    now_dt = datetime.datetime(*time.gmtime()[0:5])
    prev_dt = now_dt - datetime.timedelta(minutes=30)
    next_dt = now_dt + datetime.timedelta(minutes=30)
    intervals = min(48, len(json['results']))
    last_dt = iso_parsing(json['results'][0]['valid_to'])
    if last_dt.day != now_dt.day:
        intervals = min(96, len(json['results']))
    min_price = 1000
    max_price = -1000
    for i in range(intervals):
        item = json['results'][i]
        price = item['value_inc_vat']
        min_price = min(min_price, price)
        max_price = max(max_price, price)

    bottom = math.floor(min(min_price, -10) / 10)
    top = math.ceil(max_price / 10)
    
    multiplier = 27.5 / (top - bottom)
    zero_line = 100 + (top * 10 * multiplier)
        
    #the bounding box for the y axis is 100 to 375

    vector.set_font_size(12)
    for i in range(bottom, top+1):
        display.set_pen(DARKGREY)
        if i == 0:
            display.set_pen(GREY)
        grid_line = Polygon()
        grid_line.rectangle(MARGIN, zero_line-(i*multiplier*10), WIDTH-(3*MARGIN), 1)
        vector.draw(grid_line)
        y_label = f"{i*10}p" #no £ sign in font
        a, b, w, h = vector.measure_text(y_label)
        vector.text(y_label, WIDTH-(2*MARGIN)+2, int(zero_line-(i*multiplier*10)+(h/2)))

    for i in reversed(range(intervals)):
        item = json['results'][i]
        price = float(item['value_inc_vat'])
        price_colour = pricing_colour(price)
        from_dt = iso_parsing(item['valid_from'])
        until_dt = iso_parsing(item['valid_to'])
        if from_dt <= now_dt < until_dt:
            current_price = price
        if from_dt <= prev_dt < until_dt:
            prev_price = price
        if from_dt <= next_dt < until_dt:
            next_price = price
        if now_dt >= until_dt:
            price_colour = GREY
        x = ((intervals - 1 - i) * 9) + 15
        r = 4
        if intervals > 48:
            x = ((intervals - 1 - i) * 4.5) + 15
            r = 2
        y = zero_line - (price * multiplier)
        if from_dt.hour % 3 == 0 and from_dt.minute == 0:
            display.set_pen(DARKGREY)
            grid_line = Polygon()
            grid_line.rectangle(x, 100, 1, 275)
            vector.draw(grid_line)
            hour_text = f"{from_dt.hour:02d}"
            a, b, w, h = vector.measure_text(hour_text)
            vector.text(hour_text, int(x-(w/2)), int(375+h+3))
        display.set_pen(price_colour)
        point = Polygon()
        point.circle(x, y, r)
        vector.draw(point)
        
    # Top Middle - Time
    vector.set_font_size(48)
    display.set_pen(GREY)
    current_time = time.localtime()
    current_time_text = f"{current_time[3]:02d}:{current_time[4]:02d}"
    x, y, w, h = vector.measure_text(current_time_text)
    vector.text(current_time_text, int((WIDTH-w)/2), MARGIN+int(h))
    
    # Bottom Left - Previous Price
    vector.set_font_size(36)
    price_colour = pricing_colour(prev_price)
    display.set_pen(price_colour)
    prev_price_text = f"{prev_price:.1f}p"
    x, y, w, h = vector.measure_text(prev_price_text)
    vector.text(prev_price_text, MARGIN, HEIGHT-MARGIN)    
            
    # Bottom Center - Current Price
    vector.set_font_size(60)
    price_colour = pricing_colour(current_price)
    display.set_pen(price_colour)
    current_price_text = f"{current_price:.1f}p"
    x, y, w, h = vector.measure_text(current_price_text)
    vector.text(current_price_text, int((WIDTH-w)/2), HEIGHT-MARGIN)
    r, g, b = 0, 0, 0
    if price_colour == RED:
        r = 255
    for i in range(NUM_LEDS):
        lights.set_rgb(i, int(0.5*r), int(0.5*g), int(0.5*b))    
            
    # Bottom Right - Next Price
    vector.set_font_size(36)
    price_colour = pricing_colour(next_price)
    display.set_pen(price_colour)
    next_price_text = f"{next_price:.1f}p"
    x, y, w, h = vector.measure_text(next_price_text)
    vector.text(next_price_text, WIDTH-MARGIN-int(w), HEIGHT-MARGIN)    
            
    presto.update()
    print("END:   draw_pricing_chart")
    
def beep(frequency):
    pwm.freq(frequency)
    pwm.duty_u16(32768)  # Fixed 50% duty cycle
    time.sleep(0.05)
    pwm.duty_u16(0)    

last_updated_agile = 0
last_updated_status_minute = -1
last_touch = time.time()
screen_on = True

while True:
    if time.localtime()[3] < 06 or time.localtime()[3] >= 23:
        if time.time() - last_touch > 30 and screen_on:
            print("30 seconds since last touch, turning screen off")
            presto.set_backlight(0)
            screen_on = False
    else:
        if screen_on == False:
            print("Back to daytime, turning screen on")
            presto.set_backlight(backlight / 10)
            screen_on = True
            
    # Check if it has been over an hour since the last update
    # if it has, update the prices again.
    if time.time() - last_updated_agile > 3600:
        price_data = get_pricing()
        last_updated_agile = time.time()
    
    if last_updated_status_minute != time.localtime()[4]:
        last_updated_status_minute = time.localtime()[4]
        first_run = False
        draw_pricing_chart(price_data)

    touch.poll()
    if touch.state:
        print(touch.x, touch.y)
        if screen_on == False:
            beep(523) #C
            print("Touched whilst screen off, will turn on")
            last_touch = time.time()
            backlight = max(1, backlight)
            screen_on = True
        elif touch.x > WIDTH // 2:
            beep(659) #E
            backlight = min(10, backlight + 1)
        else:
            beep(440) #A
            backlight = max(0, backlight - 1)
        bl = backlight / 10
        print(f"Backlight: {bl}")
        presto.set_backlight(bl)        
        # Wait here until the user stops touching the screen
        while touch.state:
            touch.poll()
            time.sleep(0.02)
            
    time.sleep(0.02)
