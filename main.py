#! /usr/bin/env python

import os
import random
import time
import RPi.GPIO as GPIO
import alsaaudio
import wave
import random
from creds import *
import requests
import json
import re
from memcache import Client
import subprocess

# Settings
button = 17 #GPIO Pin with button connected

# Button config (pull high to 1 for unpressed) - GPIO.input(button)
button_pull_up_down = GPIO.PUD_UP
button_up = 1
button_down = 0

lights = [19, 26] # GPIO Pins with LED's conneted
device = "plughw:CARD=Device,DEV=0" # Name of your microphone/soundcard in arecord -L # doesn't crash

# Setup
recorded = False
servers = ["127.0.0.1:11211"]
mc = Client(servers, debug=1)
path = os.path.realpath(__file__).rstrip(os.path.basename(__file__))



def wait_for_sound_hardware():
    print "Waiting until the sound card is ready"
    try:
        subprocess.check_output("arecord -L|grep plughw:CARD=Device,DEV=0", shell=True)
	print "Sound Hardware OK"
        return True
    except:
	print "Sound Hardware not ready"
    	return False

def internet_on():
    print "Checking Internet Connection"
    try:
        r = requests.get('https://api.amazon.com/auth/o2/token')
	print "Connection OK"
        return True
    except:
	print "Connection Failed"
    	return False

	
def gettoken():
	token = mc.get("access_token")
	refresh = refresh_token
	if token:
		return token
	elif refresh:
		payload = {"client_id" : Client_ID, "client_secret" : Client_Secret, "refresh_token" : refresh, "grant_type" : "refresh_token", }
		url = "https://api.amazon.com/auth/o2/token"
		r = requests.post(url, data = payload)
		resp = json.loads(r.text)
		mc.set("access_token", resp['access_token'], 3570)
		return resp['access_token']
	else:
		return False
		

def alexa():
	GPIO.output(lights[0], GPIO.HIGH)
	url = 'https://access-alexa-na.amazon.com/v1/avs/speechrecognizer/recognize'
	headers = {'Authorization' : 'Bearer %s' % gettoken()}
	d = {
   		"messageHeader": {
       		"deviceContext": [
           		{
               		"name": "playbackState",
               		"namespace": "AudioPlayer",
               		"payload": {
                   		"streamId": "",
        			   	"offsetInMilliseconds": "0",
                   		"playerActivity": "IDLE"
               		}
           		}
       		]
		},
   		"messageBody": {
       		"profile": "alexa-close-talk",
       		"locale": "en-us",
       		"format": "audio/L16; rate=16000; channels=1"
   		}
	}
	with open(path+'recording.wav') as inf:
		files = [
				('file', ('request', json.dumps(d), 'application/json; charset=UTF-8')),
				('file', ('audio', inf, 'audio/L16; rate=16000; channels=1'))
				]	
		r = requests.post(url, headers=headers, files=files)
	if r.status_code == 200:
		for v in r.headers['content-type'].split(";"):
			if re.match('.*boundary.*', v):
				boundary =  v.split("=")[1]
		data = r.content.split(boundary)
		for d in data:
			if (len(d) >= 1024):
				audio = d.split('\r\n\r\n')[1].rstrip('--')
		with open(path+"response.mp3", 'wb') as f:
			f.write(audio)
		GPIO.output(lights[1], GPIO.LOW)
		os.system('play -q {}1sec.mp3 {}response.mp3'.format(path, path))
		GPIO.output(lights[0], GPIO.LOW)
	else:
		GPIO.output(lights, GPIO.LOW)
		for x in range(0, 3):
			time.sleep(.2)
			GPIO.output(lights[1], GPIO.HIGH)
			time.sleep(.2)
			GPIO.output(lights, GPIO.LOW)
		



def start(channel):
	last = GPIO.input(button)
        print "Please press and hold the button to ask a question"
	while True:
		val = GPIO.input(button)
		#print "GPIO VAL: " + str(val) # DEBUG
		if val != last:
			last = val
			if val == button_up and recorded == True:
				rf = open(path+'recording.wav', 'w') 
				rf.write(audio)
				rf.close()
				inp = None
				alexa()
			elif val == button_down:
				GPIO.output(lights[1], GPIO.HIGH)
				inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, device)
				inp.setchannels(1)
				inp.setrate(16000)
				inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
				inp.setperiodsize(500)
				audio = ""
				l, data = inp.read()
				if l:
					audio += data
				recorded = True
		elif val == button_down:
			l, data = inp.read()
			if l:
				audio += data
	

if __name__ == "__main__":
	GPIO.setwarnings(False)
	GPIO.cleanup()
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(button, GPIO.IN, pull_up_down=button_pull_up_down)
	GPIO.setup(lights, GPIO.OUT)
	GPIO.output(lights, GPIO.LOW)
	while wait_for_sound_hardware() == False:
		print "."
	while internet_on() == False:
		print "."
	token = gettoken()
	os.system('play -q {}1sec.mp3 {}hello.mp3'.format(path, path))
	for x in range(0, 3):
		time.sleep(.1)
		GPIO.output(lights[0], GPIO.HIGH)
		time.sleep(.1)
		GPIO.output(lights[0], GPIO.LOW)

        #GPIO.add_event_detect(button, GPIO.FALLING, callback=start, bouncetime=300) 
        #try:  
        #    while True:
        #      a = 1
        ##    print "Waiting for rising edge on port 24"  
        ##    GPIO.wait_for_edge(button, GPIO.RISING)  
        ##    print "Rising edge detected on port 24. Here endeth the third lesson."  
        #except KeyboardInterrupt:  
        #    GPIO.cleanup()       # clean up GPIO on CTRL+C exit  
        #GPIO.cleanup()           # clean up GPIO on normal exit  
        try:
	    start(0)
        except KeyboardInterrupt:  
            GPIO.cleanup()       # clean up GPIO on CTRL+C exit  
        GPIO.cleanup()           # clean up GPIO on normal exit  
