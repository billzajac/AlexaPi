#!/usr/bin/env python

import CHIP_IO.GPIO as GPIO
import time

# GPIO.setup("CSID0", GPIO.IN)
# setup(channel, direction, pull_up_down=PUD_OFF, initial=None) # GPIO.PUD_OFF,
GPIO.PUD_UP or GPIO.PUD_DOWN
#
# Waiting for an edge (GPIO.RISING, GPIO.FALLING, or GPIO.BOTH:
# This only works for the AP-EINT1, AP-EINT3, and XPO Pins on the CHIP
#    GPIO.wait_for_edge(channel, GPIO.RISING) # GPIO.FALLING

#channel = "XIO-P0"
button = "AP-EINT1"
red = "CSID0"
yellow = "CSID2"
#channel = "AP-EINT1"

def button_pressed(channel):
    print "Button Pressed: {}".format(time.strftime("%H:%M:%S"))
    GPIO.output(red, GPIO.HIGH)
    GPIO.output(yellow, GPIO.LOW)

    while GPIO.input(button):
        time.sleep(0.01)

    print "Button Released: {}".format(time.strftime("%H:%M:%S"))
    GPIO.output(red, GPIO.LOW)
    GPIO.output(yellow, GPIO.HIGH)

GPIO.setup(red, GPIO.OUT)
GPIO.setup(yellow, GPIO.OUT)
# NOTE: pull_up_down=GPIO.PUD_DOWN does not seem to work
#       Instead use a physical pull-down resistor
GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN, initial=GPIO.LOW)
#GPIO.add_event_detect(button, GPIO.RISING, button_pressed)
GPIO.add_event_detect(button, GPIO.RISING, callback=button_pressed, bouncetime=350)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()       # clean up GPIO on CTRL+C exit

GPIO.cleanup()           # clean up GPIO on normal exit
