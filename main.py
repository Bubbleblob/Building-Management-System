import Adafruit_DHT
import RPi.GPIO as GPIO
import time
import drivers
from datetime import timedelta, datetime
from threading import Thread, Lock, Event
import decimal
from signal import pause
from cimis import cimis
from cimis import get_cimis_data

DHT_SENSOR = Adafruit_DHT.DHT11		# this line defines the sensor object we will use
DHT_PIN = 17				# a variable that defines the GPIO pin we are using
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(16, GPIO.IN) 				# PIR Sensor
GPIO.setup(12, GPIO.OUT)				# Green LED
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)	# Green Button
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)	# Red Button
GPIO.setup(32, GPIO.IN, pull_up_down=GPIO.PUD_UP)	# Blue Button
GPIO.setup(38, GPIO.OUT)				# Red LED
GPIO.setup(40, GPIO.OUT)				# Blue LED
GPIO.setup(12, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(38, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(40, GPIO.OUT, initial=GPIO.LOW)
GPIO.output(12, 0)
GPIO.output(38, 0)
GPIO.output(40, 0)
display = drivers.Lcd()
mutex = Lock()

door_flag = 0			# 0:door closed, 1:door opened
ambient_light_flag = 0		# 0:green led off, 1:greed led on
hvac_flag = 0 			# 0:off, 1:AC, 2:Heater 
start_time = 10
desired_temp = 75
temp_to_print = 0
humidity_to_print = 0
weather_index = 0
door_open_temp = 0
starting_hour = -1
HOUR = 60 * 60

def displayLCD():
	global door_flag
	global ambient_light_flag
	global hvac_flag
	global desired_temp
	global temp_to_print
	global weather_index
	global hvac_pause

	door = "n/a"
	light = "n/a"
	hvac = "n/a"
	
	# checking flags to print correct statements on LCD
	if ambient_light_flag == 0:
		light = "OFF"
	else:
		light = "ON"
	
	if hvac_flag == 0:
		hvac = "OFF"
	elif hvac_flag == 1:
		hvac = "AC"
	elif hvac_flag == 2:
		hvac = "HEAT"

	# if door is open
	if door_flag == 0:
		door = "SAFE"
		if hvac_flag == 1:
			GPIO.output(40, 1)
		elif hvac_flag == 2:
			GPIO.output(38, 1)
	# if door is closed
	else:
		door = "OPEN"
		hvac = "OFF"
		GPIO.output(40, 0)
		GPIO.output(38, 0)
		

	# convert temp and weather index to str for printing on LCD
	d_temp = str(desired_temp)
	temp = str(temp_to_print)
	weather = str(weather_index)

	# print values out to LCD
	display.lcd_clear()
	display.lcd_display_string(weather + "/" + d_temp + "     D:" + door, 1)
	display.lcd_display_string("H:" + hvac + "     L:" + light, 2)	

def getHVAC(): 
	temp_event.wait()

	global temp_to_print
	global humidity_to_print
	global weather_index
	global door_flag
	global mutex

	global desired_temp
	global hvac_flag

	temp1 = 0.0
	temp2 = 0.0
	temp3 = 0.0
	humidity1 = 0.0
	humidity2 = 0.0
	humidity3 = 0.0
	tempF = 0.0
	current_hour = starting_hour
	counter = 0
	
	while temp_event.is_set():
		mutex.acquire()
		
		if door_flag == 0:
			# sample temp and humidity from dht and store in global variables
			data = get_cimis_data(current_hour)
			while(data is None or data.get_humidity() is None):
				print("Attempting to get CIMIS data for time " + str(current_hour) + ":00")
				if data is None:
					print("Failed to get data from CIMIS. Trying again in an hour")
				time.sleep(HOUR)
				data = get_cimis_data(current_hour)

			if data.get_humidity() is not None:
				humidity_to_print = float(data.get_humidity())

			while True:
				humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
				if temperature is not None:
					temp1 = temperature
					break	
			time.sleep(0.3)

			while True:
				humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
				if temperature is not None:
					temp2 = temperature
					break
			time.sleep(0.3)
	
			while True:
				humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
				if temperature is not None:
					temp3 = temperature
					break
			time.sleep(0.3)
	
			temp_to_print = round(((temp1 + temp2 + temp3) / 3) * 9/5 + 32)
			weather_index = round(temp_to_print + 0.05 * humidity_to_print)
	
			print("humidity: " + str(humidity_to_print))
			print("temp: " + str(temp_to_print))
			displayLCD()
		else:
			time.sleep(0.9)
			displayLCD()
		mutex.release()
		time.sleep(0.1)
		
def checkSecurity(channel):
	global door_flag
	global mutex

	# door opening
	if door_flag == 0:
		door_flag = 1

		mutex.acquire()
		display.lcd_clear()
		display.lcd_display_string("   DOOR OPEN", 1)
		display.lcd_display_string("  HVAC HALTED", 2)
		time.sleep(3)						# display on lcd for 3 sec
		mutex.release()

	# door closing
	elif door_flag == 1:
		door_flag = 0

		mutex.acquire()
		display.lcd_clear()			
		display.lcd_display_string("  DOOR CLOSED", 1)
		display.lcd_display_string("  HVAC RESUME", 2)
		time.sleep(3)						# display on lcd for 3 sec 
		mutex.release()
	
def raiseTemp(channel):
	global temp_to_print
	global desired_temp
	global weather_index
	global hvac_flag
	global door_flag
	global mutex

	current_state = hvac_flag		# 0:off, 1:AC, 2:Heater

	if door_flag == 0:
		# if red button is clicked desired_temp++ if in range
		if desired_temp < 85:
			desired_temp += 1

		# for AC led to turn on
		if weather_index >= desired_temp + 3:
			GPIO.output(40, 1)
			hvac_flag = 1
			
			if current_state != hvac_flag:
				mutex.acquire()
				display.lcd_clear()
				display.lcd_display_string("HVAC AC ON", 1)
				time.sleep(3)
				mutex.release()
		# for Heater led to turn on
		elif weather_index <= desired_temp - 3:
			GPIO.output(38, 1)
			hvac_flag = 2
			
			if current_state != hvac_flag:
				mutex.acquire()
				display.lcd_clear()
				display.lcd_display_string("HVAC HEATER ON", 1)
				time.sleep(3)
				mutex.release()
		# turn off AC and Heater
		else:
			GPIO.output(40, 0)
			GPIO.output(38, 0)
			hvac_flag = 0

			if current_state == 1:
				mutex.acquire()
				display.lcd_clear()
				display.lcd_display_string("HVAC AC OFF", 1)
				time.sleep(3)
				mutex.release()
			elif current_state == 2:
				mutex.acquire()
				display.lcd_clear()
				display.lcd_display_string("HVAC HEATER OFF", 1)
				time.sleep(3)
				mutex.release()

def lowerTemp(channel):
	global temp_to_print
	global desired_temp
	global weather_index
	global hvac_flag
	global door_flag

	current_state = hvac_flag 		# 0:off, 1:AC, 2:Heater
	
	if door_flag == 0:
		# if blue button is clicked desired_temp-- if in range
		if desired_temp > 65:
			desired_temp -= 1
	
		# for AC led to turn on
		if weather_index >= desired_temp + 3:
			GPIO.output(40, 1)
			hvac_flag = 1

			if current_state != hvac_flag:
				mutex.acquire()
				display.lcd_clear()
				display.lcd_display_string("HVAC AC ON", 1)
				time.sleep(3)
				mutex.release()
		# for Heater led to turn on
		elif weather_index <= desired_temp - 3:
			GPIO.output(38, 1)
			hvac_flag = 2

			if current_state != hvac_flag:
				mutex.acquire()
				display.lcd_clear()
				display.lcd_display_string("HVAC HEATER ON", 1)
				time.sleep(3)
				mutex.release()
		# turn off AC and Heater
		else:
			GPIO.output(38, 0)
			GPIO.output(40, 0)
			hvac_flag = 0

			if current_state == 1:
				mutex.acquire()
				display.lcd_clear()
				display.lcd_display_string("HVAC AC OFF", 1)
				time.sleep(3)
				mutex.release()
			elif current_state == 2:
				mutex.acquire()
				display.lcd_clear()
				display.lcd_display_string("HVAC HEATER OFF", 1)
				time.sleep(3)
				mutex.release()

def checkPIR(channel):
	global start_time
	global ambient_light_flag

	# motion detected
	if GPIO.input(16) == 1:
		event.clear() 
		GPIO.output(12, 1)
		ambient_light_flag = 1
	# motion not detected
	else:
		print("create thread")
		t1 = Thread(target=timer, daemon=True) # thread for timer
		t1.start() # start 10 sec timer
		event.set()

def timer():
	event.wait()
	global ambient_light_flag

	start_time = time.time()
	current_time = time.time()
	while current_time - start_time < 10 and event.is_set():
		current_time = time.time()
	if current_time - start_time > 10:
		ambient_light_flag = 0
		GPIO.output(12, 0)	

if __name__ == "__main__":
	try:

		starting_hour = time.localtime(time.time()).tm_hour - 2	
		GPIO.add_event_detect(18, GPIO.RISING, callback=checkSecurity, bouncetime=150) # for green button
		GPIO.add_event_detect(22, GPIO.RISING, callback=raiseTemp, bouncetime=150) # for red button
		GPIO.add_event_detect(32, GPIO.RISING, callback=lowerTemp, bouncetime=150) # for blue button
		GPIO.add_event_detect(16, GPIO.BOTH, callback=checkPIR, bouncetime=150) # for PIR sensor

		event = Event()
		temp_event = Event()
		security_event = Event()

		temp_thread = Thread(target=getHVAC, daemon=True)
		temp_thread.start()
		temp_event.set() # set event for first print of LCD

		while True:
			time.sleep(1e6)
	except KeyboardInterrupt:
		print("exiting program")
		display.lcd_clear()
	finally:
		GPIO.cleanup()
