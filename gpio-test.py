#!/usr/bin/python

import time
import threading
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)

class GpioInput:
  def __init__(self, pin, name = "", activeHigh = True):
    self._name = name
    self._pin = pin
    if activeHigh:
      self._activeValue = 1
      GPIO.setup(self._pin, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
    else:
      self._activeValue = 0
      GPIO.setup(self._pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)    

  def __repr__(self):
    return "<GpioInput pin=%d name=%r>" % (self._pin, self._name)

  def __str__(self):
    return self.__repr__()  

  def getActive(self):
    return GPIO.input(self._pin) == self._activeValue


class Button:
  def __init__(self, gpioInput, callback, maxTimeMs = 2000):
    self._gpio = gpioInput
    self._callback = callback
    self._acumValue = 0x0 # Released
    self._activeTime = 0
    self._maxTime = maxTimeMs / 10

  def __repr__(self):
    return "<Button gpio=%r activeTime=%d>" % (self._gpio, self._activeTime)

  def __str__(self):
    return self.__repr__()  
  
  def _runCallback(self, activeTime):
     self._callback(self._gpio, activeTime * 10)
  
  # Must be called with 0.01 secs interval    
  def poll(self):
    # Shift in current GPIO value to debounce the pin.
    # Must be 4 in a row of the same value to be considered stable
    self._acumValue <<= 1
    self._acumValue |= self._gpio.getActive()
    self._acumValue &= 0xF

    if self._acumValue == 0xF: # Stable active
      self._activeTime += 1
      if self._activeTime == self._maxTime: # Reached max active time
        self._runCallback(self._maxTime) # report it immediately
        # But don't reset _activeTime so user must release button before a new report

    elif self._acumValue == 0x0: # Stable inactive
      # Run callback if been active and not already reported
      if self._activeTime > 0 and self._activeTime <= self._maxTime: 
        self._runCallback(self._activeTime)        
      
      self._activeTime = 0 # reset
      
    # Return False when stable inactive, meaning True to keep polling
    return self._acumValue != 0x0
    
  def check(self):
    if self._gpio.getActive():
      self._activeTime = 1
      return True
    else:      
      return False

class ButtonsChecker(threading.Thread):
  def __init__(self, buttons):
    threading.Thread.__init__(self)
    self._buttons = buttons

  def _pollButtons(self):
    while True:
      keepPolling = False
      for b in self._buttons:
        if b.poll():
          keepPolling = True
        
      if not keepPolling:
        break

      time.sleep(0.01)

  def _checkButtons(self):
    startPolling = False
    for b in self._buttons:
      if b.check():
        startPolling = True
      
    if startPolling:
      self._pollButtons()

  def run(self):
    while True:
      self._checkButtons()
      time.sleep(0.1)    


def buttonPressed(gpio, activeTimeMs):
  print "Button pressed gpio=%r activeTimeMs=%d" % (gpio, activeTimeMs)


gp15 = GpioInput(15, "ButtonUp", activeHigh=False)
gp16 = GpioInput(16, "ButtonDown", activeHigh=False)

buttons = []
buttons.append(Button(gp15, buttonPressed, maxTimeMs=2000))
buttons.append(Button(gp16, buttonPressed, maxTimeMs=2000))

bc = ButtonsChecker(buttons)
bc.daemon = True
bc.start()

while True:
  time.sleep(1)
  
GPIO.cleanup()
