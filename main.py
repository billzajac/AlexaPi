#! /usr/bin/env python

import datetime
import command
import os
import signal
import subprocess
import random
import time
#import RPi.GPIO as GPIO
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

global playback_subprocess_pid
playback_subprocess_pid = None

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
    # First ensure that we actually recorded something reasonable
    # sox_process = subprocess.Popen('sox -t .s16 recording.wav -n stat 2>&1|grep Length|awk \'{print $3}\'', stdout=subprocess.PIPE)
    # out, err = sox_process.communicate()
    try:
        sox_process = subprocess.Popen(['/usr/bin/sox', '-t', '.s16', path+'recording.wav', '-n', 'stat'], stderr=subprocess.PIPE)
        out, err = sox_process.communicate()
        recording_length = float(re.findall(r'Length.*(\d+\.\d+)', err)[0])
        if recording_length < 1.5:
            print "Recording was too short: {}".format(recording_length)
            return
    except:
        print "Failed to determine the length of the recording"
        return

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
        #os.system('play -q {}1sec.mp3 {}response.mp3'.format(path, path))
        #subprocess.call(['play', '-q', '{}1sec.mp3'.format(path), '{}response.mp3'.format(path)])
        # The os.setsid() is passed in the argument preexec_fn so it's run after the fork() and before  exec() to run the shell.
        #playback_subprocess = subprocess.Popen('play -q {}1sec.mp3 {}response.mp3'.format(path, path), close_fds=True, shell=True, preexec_fn=os.setsid)
        global playback_subprocess
        #playback_subprocess = subprocess.Popen('play -q {}1sec.mp3 {}response.mp3'.format(path, path), shell=True, preexec_fn=os.setsid)
        playback_subprocess = subprocess.Popen('lame --decode {}response.mp3 - | aplay -'.format(path), shell=True, preexec_fn=os.setsid)

def button_pressed():
    print "Button Pressed: {}".format(time.strftime("%H:%M:%S"))

    # Ensure that we don't allow ghost button presses
    # I often find a bounce about 2 seconds after the initial
    #global last_button_release
    #if last_button_release:
    #    if (datetime.datetime.now() - last_button_release).total_seconds() > 2:
    #        last_button_release = None
    #    else:
    #        print "Button press too close, probably a bounce.  Ignoring."
    #        return

    global playback_subprocess_pid
    if playback_subprocess_pid:
        print "Subprocess PID exists: {} Let's kill it!".format(playback_subprocess_pid)
        try:
            # source: http://stackoverflow.com/questions/4789837/how-to-terminate-a-python-subprocess-launched-with-shell-true
            process_group_id = os.getpgid(playback_subprocess_pid)
            print "Killing subprocess group ID: {}".format(process_group_id)
            os.killpg(process_group_id, signal.SIGKILL) # send the signal to all the process groups (SIGKILL/SIGTERM)
            print "Successful termination!"
        except:
            print "Failed to terminate process"
    # print "No process running to terminate"

    record_and_process()

def record_and_process():
    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, device)
    inp.setchannels(1)
    inp.setrate(16000)
    inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    inp.setperiodsize(500)
    audio = ""
    l, data = inp.read()
    if l:
        audio += data

    status, output = command.getstatusoutput('/usr/local/lb/Button/bin/getButton')
    while status != 0:
        l, data = inp.read()
        if l:
            audio += data
        val = GPIO.input(button)
        status, output = command.getstatusoutput('/usr/local/lb/Button/bin/getButton')

    # Button is up now
    print "Button Released: {}".format(time.strftime("%H:%M:%S"))

    # This is used to ensure that we don't allow ghost button presses
    # I often find a bounce about 2 seconds after the initial
    #global last_button_release
    #last_button_release = datetime.datetime.now()

    rf = open(path+'recording.wav', 'w') 
    rf.write(audio)
    rf.close()
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
      status, output = command.getstatusoutput('/usr/local/lb/Button/bin/getButton')
      if status != 0:
        button_pressed()
    
