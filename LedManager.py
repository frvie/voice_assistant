import threading
import time

from neopixel import *


class LedManager(threading.Thread):
    def __init__(self, action, status):
        threading.Thread.__init__(self)
        self.strip = self.setupPins()
        self.action = action
        self.status = status
        self.lastAction = None

    def run(self):
        while (True):
            self.checkAction()
            time.sleep(1)

    # Define functions which animate LEDs in various ways.
    def colorWipe(self, strip, color):
        """Wipe color across display a pixel at a time."""
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
            strip.show()

    def processAnimation(self, strip, color, wait_ms=150):
        while self.action == "processing":
            if self.status == "apiai":
                wait_ms = 500
            for q in range(3):
                for i in range(0, strip.numPixels(), 3):
                    # print ('q: %s i:%s' % (q, i))
                    strip.setPixelColor(i + q, color)
                strip.show()
                time.sleep(wait_ms / 1000.0)
                for i in range(0, strip.numPixels(), 3):
                    strip.setPixelColor(i + q, 0)
        self.status = ''

    def colorPulse(self, args):
        # for j in range(4):
        for i in range(0, 255, 5):
            if args == "warning":
                color = Color(i, i, 0)
            elif args == "finish":
                color = Color(0, 0, i)
            else:
                color = Color(i, 0, 0)
            self.colorWipe(self.strip, color)

        time.sleep(2)

        for i in range(0, 255, 5):
            if args == "warning":
                color = Color(255 - i, 255 - i, 0)
            elif args == "finish":
                color = Color(0, 0, 255 - i)
            else:
                color = Color(255 - i, 0, 0)
            self.colorWipe(self.strip, color)

    def setupPins(self):
        """
        Setup the raspberry pins.
        :return: strip, object that contains all pins configurations
        """
        # LED strip configuration:
        LED_COUNT = 12  # Number of LED pixels.
        LED_PIN = 18  # GPIO pin connected to the pixels (18 uses PWM!).
        LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
        LED_DMA = 5  # DMA channel to use for generating signal (try 5)
        LED_BRIGHTNESS = 50  # Set to 0 for darkest and 255 for brightest
        LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
        LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53
        LED_STRIP = ws.WS2811_STRIP_GRB  # Strip type and colour ordering
        # Create NeoPixel object with appropriate configuration.
        strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL,
                                  LED_STRIP)
        # Intialize the library (must be called once before other functions).
        # strip._cleanup()
        strip.begin()
        return strip

    def hearing(self):
        color = Color(255, 255, 255)
        self.colorWipe(self.strip, color)

    def processing(self):
        color = Color(255, 255, 255)
        self.processAnimation(self.strip, color)

    def cleanup(self):
        color = Color(0, 0, 0)
        self.colorWipe(self.strip, color)

    def error(self):
        self.colorPulse("error")
        time.sleep(0.5)
        self.action = "led_off"

    def finishProcess(self):
        self.colorPulse("finish")
        time.sleep(0.5)
        self.action = "led_off"

    def noRecognize(self):
        self.colorPulse("warning")
        time.sleep(0.5)
        self.action = "led_off"

    def checkAction(self):
        """
        Define the LEDs light mode.
        :return: void
        """
        if self.action == "detected":
            self.hearing()
        elif self.action == "processing":
            self.processing()
        elif self.action == "led_off":
            self.cleanup()
        elif self.action == "error":
            self.error()
        elif self.action == "finish":
            self.finishProcess()
        elif self.action == "warning":
            self.noRecognize()
