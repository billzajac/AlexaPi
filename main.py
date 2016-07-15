#! /usr/bin/env python

import pprint
import datetime
import commands
import os
import signal
import subprocess
import random
import time
import alsaaudio
import wave
import random
from creds import *
import requests
import json
import re


device = "sysdefault:CARD=mxsbuiltinaudio" # Name of your microphone/soundcard in arecord -L # doesn't crash

# Setup
path = os.path.realpath(__file__).rstrip(os.path.basename(__file__))
playback_subprocess = None

global token
token = None

global token_updated_at
token_updated_at = datetime.datetime.now() - datetime.timedelta(hours = 2)

def wait_for_sound_hardware():
    print "Waiting until the sound card is ready"
    try:
        # USB sound card
        subprocess.check_output("arecord -L|grep {}".format(device), shell=True)
        print "  Recording Device: OK - {}".format(device)
        print "  Output Device: OK - {}".format(device)

        # Bluetooth speaker
        # bluetooth_address = 'A0:E9:DB:00:73:49'
        # subprocess.check_output("hcitool con|grep {}".format(bluetooth_address), shell=True)
        # print "  Output Device: OK - {}".format(bluetooth_address)

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
    global token_updated_at
    global token
    refresh = refresh_token
    if (datetime.datetime.now() - token_updated_at).total_seconds() < 3570:
        return token
    elif refresh:
        payload = {"client_id" : Client_ID, "client_secret" : Client_Secret, "refresh_token" : refresh, "grant_type" : "refresh_token", }
        url = "https://api.amazon.com/auth/o2/token"
        r = requests.post(url, data = payload)
        resp = json.loads(r.text)
        token = resp['access_token']
        token_updated_at = datetime.datetime.now()
        return token
    else:
        return False
        
def alexa():
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
    print('Sending request to Amazon')
    with open(path+'recording.wav') as inf:
        files = [
                ('file', ('request', json.dumps(d), 'application/json; charset=UTF-8')),
                ('file', ('audio', inf, 'audio/L16; rate=16000; channels=1'))
                ]   
        r = requests.post(url, headers=headers, files=files)
    if r.status_code == 200:
        print('Successful post to Amazon')
        for v in r.headers['content-type'].split(";"):
            if re.match('.*boundary.*', v):
                boundary =  v.split("=")[1]
        data = r.content.split(boundary)
        for d in data:
            if (len(d) >= 1024):
                audio = d.split('\r\n\r\n')[1].rstrip('--')
        with open(path+"response.mp3", 'wb') as f:
            f.write(audio)
        print('Playing {}response.mp3').format(path)
        subprocess.call('lame --decode {}response.mp3 - | aplay -'.format(path), shell=True)
    else:
      print('Unsuccessful post to Amazon: return code: {}').format(r.status_code)
      pp = pprint.PrettyPrinter(indent=4)
      pp.pprint(r.json())


def button_pressed():
    print "Button Pressed: {}".format(time.strftime("%H:%M:%S"))
    # We will fork the arecord process to the background and wait until the button is released to kill it

    # The os.setsid() is passed in the argument preexec_fn so it's run after the fork() and before  exec() to run the shell.
    record_subprocess = subprocess.Popen('arecord -f S16_LE -c 1 -r 16000 recording.wav', shell=True, preexec_fn=os.setsid)
    record_subprocess_pid = record_subprocess.pid
    record_subprocess_group_id = os.getpgid(record_subprocess_pid)

    status, output = commands.getstatusoutput('/usr/local/lb/Button/bin/getButton')
    while status != 0:
            status, output = commands.getstatusoutput('/usr/local/lb/Button/bin/getButton')
            time.sleep(0.2)
    os.killpg(record_subprocess_group_id, signal.SIGKILL) # send the signal to all the process groups (SIGKILL/SIGTERM)
    # why get fancy.  let's go crazy
    subprocess.call(['killall', 'arecord'])

    # Button is up now
    print "Button Released: {}".format(time.strftime("%H:%M:%S"))

    alexa()

if __name__ == "__main__":
    while wait_for_sound_hardware() == False:
        print "."
        time.sleep(1)
    while internet_on() == False:
        print "."
    token = gettoken()

    os.system('lame --decode {}hello.mp3 - | aplay -'.format(path))

    print "Please press and hold the button to ask a question"

    while True:
      status, output = commands.getstatusoutput('/usr/local/lb/Button/bin/getButton')
      if status != 0:
        button_pressed()
    
