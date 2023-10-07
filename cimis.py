from __future__ import print_function
import json
from urllib.request import urlopen
import urllib
from datetime import datetime, timedelta
import time

appKey = '792e4062-3ca4-4810-9651-8b10a24744a2'
station = 75

class cimis:
	def __init__(self, date, hour, humidity):
		self.date = date
		self.hour = hour
		self .humidity = humidity
	def get_date(self):
		return self.date
	def get_hour(self):
		return self.hour
	def get_humidity(self):
		return self.humidity

def get_cimis_data (current_hour):
	if current_hour == 0 or current_hour > time.localtime(time.time()).tm_hour:
		date = datetime.strftime(datetime.now() - timedelta(1), '%Y-%y')
	else:
		date = datetime.now().strftime('%Y-%m-%d')
	data = run_cimis(appKey, station, date, date)
	if data is None:
		return None

	# creates object for retrieved data
	d = cimis( data[current_hour-1]['Date'],     
			data[current_hour-1]['Hour'], 
			data[current_hour-1]['HlyRelHum']['Value'],
			)
	return d
   
def retrieve_cimis_data(url, target):
	try:
		content = urlopen(url).read().decode('utf-8')        
		assert(content is not None)
		return json.loads(content)
	except urllib.error.HTTPError as e:
		print("Could not resolve the http request at this time")
		error_msg = e.read()
		print(error_msg)
		return None
	except urllib.error.URLError:
		print('Could not access the CIMIS database.Verify that you have an active internet connection and try again.')
		return None
	except: #json.decoder.JSONDecodeError:  #ConnectionResetError:
		print("CMIS request was rejected")
		return None
 
def run_cimis(appKey, station, start, end):
	ItemList = ['hly-rel-hum']

	dataItems = ','.join(ItemList)
    
	url = ('http://et.water.ca.gov/api/data?appKey=' + appKey + '&targets=' 
		+ str(station) + '&startDate=' + start + '&endDate=' + end + 
		'&dataItems=' + dataItems +'&unitOfMeasure=M')
            
	data = retrieve_cimis_data(url, station)
	if(data is None):
		return None    
	else:
		return data['Data']['Providers'][0]['Records']
