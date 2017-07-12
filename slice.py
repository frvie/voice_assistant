import pyaudio
import collections
import time
import os
import wave
import sys
import logging
import pyttsx3
from gtts import gTTS
import urllib3
import json

import apiai
import speech_recognition as sr
import threading

from datetime import datetime

logging.basicConfig()
logger = logging.getLogger("slice")
logger.setLevel(logging.INFO)



class LedManager(object):
    def __init__(self, action, status):
        threading.Thread.__init__(self)
        #self.strip = self.setupPins()
        self.action = action
        self.status = status
        self.lastAction = None

    def run(self):
        while (True):
            self.checkAction()
            time.sleep(1)

    def checkAction(self):
        logger.info (self.action)


def internet_on():
    http = urllib3.PoolManager()
    for timeout in [1, 5, 10, 15]:
        try:
            url = 'http://google.com'
            response = http.request('GET', url, timeout)
            return response.status
        except urllib3.exceptions.NewConnectionError:
            print('error')
    return False



class RingBuffer(object):
    """Ring buffer to hold audio from PortAudio"""

    def __init__(self, size=4096):
        self._buf = collections.deque(maxlen=size)

    def extend(self, data):
        """Adds data to the end of buffer"""
        self._buf.extend(data)

    def get(self):
        """Retrieves data from the beginning of buffer and clears it"""
        tmp = bytes(bytearray(self._buf))
        self._buf.clear()
        return tmp

class AudioMgr(object):
    def __init__(self, sample_rate=44100, chunk_size=4096, energy_threshold=300, mic_name='Echo Cancelling Speakerphone (J'):
        threading.Thread.__init__(self)
        self.speech=''
        self.audio=None
        self.audio_timestamp = datetime.now().isoformat(timespec='microseconds')

        # setting up recognition callback
        def callback(recognizer, audio):
            # received audio data, now we'll recognize it using Google Speech Recognition
            try:
                if audio:
                    self.audio = audio
                    self.audio_timestamp = datetime.now().isoformat(timespec='microseconds')
                    self.speech = recognizer.recognize_google(audio)

            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                print("Could not request results from Google Speech Recognition service; {0}".format(e))

        self.rec = sr.Recognizer()
        for i, microphone_name in enumerate(sr.Microphone.list_microphone_names()):
            if microphone_name == mic_name:
                self.mic = sr.Microphone(device_index=i, sample_rate=sample_rate, chunk_size=chunk_size)
                break
        self.rec.energy_threshold = energy_threshold


        with self.mic as source:
            self.rec.adjust_for_ambient_noise(source)  # we only need to calibrate once, before we start listening
        # start listening in the background (note that we don't have to do this inside a `with` statement)
        logger.info('setting up the ambient listener')
        self.stop_listening = self.rec.listen_in_background(self.mic, callback)

    def run(self):
        time.sleep(0.05)

    def get (self):
        self.audio=None
        self.speech=''
        self.audio_timestamp=''


class VoiceAssistant(object):

    def __init__(self, apiai_key='54e6635967124763a256ccb31fb9de4b', session_id='Room', sample_rate=44100, chunk_size=4096, energy_threshold=300):

        #setting up API.AI object and variables
        self.ai_key = apiai.ApiAI(apiai_key)
        self.ai_session_id = session_id
        self.ai_timestamp = []
        self.ai_conversation = []
        self.ai_response_dict = {}

        # self.ambient_audio = AudioManager()
        self.audio_instance = AudioMgr(sample_rate, chunk_size, energy_threshold)
         #setting up visual feedback
        self.lights = LedManager('off', '')

    def speak(self, message):
        # import os
        engine = pyttsx3.init()
        #engine.setProperty('voice', 'mb-us1')
        engine.setProperty('voice', 'us1')
        engine.setProperty('rate', 185)
        engine.say(message)
        engine.runAndWait()
        # os.system("espeak -s 160 -g 0.1 -a 100 -v mb/mb-us1 -p70 -k20 '"+message+"'")

    def dialog(self, text_message = '', original_audio = None, apiai_acc = 0.4 ):

        speech=''
        logger.info('Assistant thinks you said \'' + text_message + '\'')

        #preparing API.AI request
        request = self.ai_key.text_request()
        request.session_id = self.ai_session_id
        request.query = text_message

        response = json.loads(request.getresponse().read())
        if (not response):  # no json returned from apiai
            return speech

        #Obtaining API.AI matching score
        score = response['result']['score']
        logger.info('Action Matching: ' + str(score * 100) + '%')
        #Parsing Action
        if score >= apiai_acc:
            result = response['result']
            actionIncomplete = result.get('actionIncomplete', False)
            speech = response['result']['fulfillment']['speech']
            logger.info(speech)

            #saving dialog context
            self.ai_timestamp.append(response['timestamp'])
            self.ai_conversation.append([response['result']['resolvedQuery'], speech, score, original_audio, response['timestamp']])

            if not actionIncomplete:
                logger.info('request fulfilled')
                self.lights.action = "finish"
                #adding dialog to dictionary when action is fulfilled
                self.ai_response_dict[self.ai_session_id]=[]
                self.ai_response_dict[self.ai_session_id].append({  'type' : 'voice_interaction',
                                                                    'caller_device': response['sessionId'],
                                                                    'action' : response['result']['action'],
                                                                    'params' : response['result']['parameters'],
                                                                    'begin' : self.ai_timestamp[0],
                                                                    'end' : self.ai_timestamp[-1],
                                                                    'conversation' : self.ai_conversation})
                #reseting temporary context variables
                self.ai_timestamp = []
                self.ai_conversation = []

                request_status = 1
                hotword_triggered = 0
            else:
                request_status = 0
                hotword_triggered = 1
        else:
            hotword_triggered = 0
            self.lights.action = "warning"
        print (self.ai_response_dict)
        return speech


#============================================


def main():
    agent = VoiceAssistant(session_id='Room17', sample_rate=44100, chunk_size=4096, energy_threshold=3000)
    while True:
        time.sleep(0.05)
        if len(agent.audio_instance.speech)>0:
            ai_return = agent.dialog(agent.audio_instance.speech, agent.audio_instance.audio)
            agent.speak(ai_return)
            agent.audio_instance.get()

if __name__ == '__main__':
    main()



