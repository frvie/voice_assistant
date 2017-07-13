import pyaudio
import collections
import time
import os
import wave
import sys
import logging
import pyttsx3
import urllib3
import json

import apiai
import speech_recognition as sr
import threading

from datetime import datetime


TOP_DIR = os.path.dirname(os.path.abspath(__file__))
DETECT_DING = os.path.join(TOP_DIR, "ding.wav")
DETECT_DONG = os.path.join(TOP_DIR, "dong.wav")

#import snowboydetect
#RESOURCE_FILE = os.path.join(TOP_DIR, "resources/common.res")



logging.basicConfig()
logger = logging.getLogger("slice")
logger.setLevel(logging.INFO)

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
        self.audio_in_use = False
        self.audio_timestamp = datetime.now().isoformat(timespec='microseconds')

        # setting up recognition callback
        def callback(recognizer, audio):
            # received audio data, now we'll recognize it using Google Speech Recognition
            try:
                if not self.audio_in_use:
                    self.audio_in_use = True
                    self.audio = audio
                    self.audio_timestamp = datetime.now().isoformat(timespec='microseconds')
                    self.speech = recognizer.recognize_google(audio)
                    self.audio_in_use = False
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                print("Could not request results from Google Speech Recognition service; {0}".format(e))

        self.rec = sr.Recognizer()
        for i, microphone_name in enumerate(sr.Microphone.list_microphone_names()):
            if microphone_name == mic_name:
                self.mic = sr.Microphone(sample_rate=sample_rate, chunk_size=chunk_size)
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


class RingBuffer(object):
    """Ring buffer to hold audio from PortAudio"""
    def __init__(self, size = 4096):
        self._buf = collections.deque(maxlen=size)

    def extend(self, data):
        """Adds data to the end of buffer"""
        self._buf.extend(data)

    def get(self):
        """Retrieves data from the beginning of buffer and clears it"""
        tmp = bytes(bytearray(self._buf))
        self._buf.clear()
        return tmp


def play_audio_file(fname=DETECT_DING):
    """Simple callback function to play a wave file. By default it plays
    a Ding sound.

    :param str fname: wave file name
    :return: None
    """
    ding_wav = wave.open(fname, 'rb')
    ding_data = ding_wav.readframes(ding_wav.getnframes())
    audio = pyaudio.PyAudio()
    stream_out = audio.open(
        format=audio.get_format_from_width(ding_wav.getsampwidth()),
        channels=ding_wav.getnchannels(),
        rate=ding_wav.getframerate(), input=False, output=True)
    stream_out.start_stream()
    stream_out.write(ding_data)
    time.sleep(0.2)
    stream_out.stop_stream()
    stream_out.close()
    audio.terminate()


class VoiceAssistant(object):

    def __init__(self, apiai_key='54e6635967124763a256ccb31fb9de4b', session_id='Room', sample_rate=44100, chunk_size=4096, energy_threshold=300, ):

        def audio_callback(in_data, frame_count, time_info, status):
            self.ring_buffer.extend(in_data)
            play_data = chr(0) * len(in_data)
            return play_data, pyaudio.paContinue

        #self.detector = snowboydetect.SnowboyDetect(
        #    resource_filename=resource.encode(), model_str=model_str.encode())
        #self.ring_buffer = RingBuffer(
        #    self.detector.NumChannels() * self.detector.SampleRate() * 5)

        self.audio = pyaudio.PyAudio()
        #self.stream_in = self.audio.open(
            input=True, output=False,
            format=self.audio.get_format_from_width(
                self.detector.BitsPerSample() / 8),
            channels=self.detector.NumChannels(),
            rate=self.detector.SampleRate(),
            frames_per_buffer=2048,
            stream_callback=audio_callback)

        self.stream_in = self.audio.open(
            input = True, output = False,
            format = self.audio.get_format_from_width(
            self.detector.BitsPerSample() / 8),
            channels = self.detector.NumChannels(),
            rate = self.detector.SampleRate(),
            frames_per_buffer = 2048,
            stream_callback = audio_callback)


    #setting up API.AI object and variables
        self.ai_key = apiai.ApiAI(apiai_key)
        self.ai_session_id = session_id
        self.ai_timestamp = []
        self.ai_conversation = []
        self.ai_response_dict = {}

        # self.ambient_audio = AudioManager()
        #self.audio_instance = AudioMgr(sample_rate, chunk_size, energy_threshold)
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

    def start(self, detected_callback=play_audio_file,
              interrupt_check=lambda: False,
              sleep_time=0.03):
        """
        Start the voice detector. For every `sleep_time` second it checks the
        audio buffer for triggering keywords. If detected, then call
        corresponding function in `detected_callback`, which can be a single
        function (single model) or a list of callback functions (multiple
        models). Every loop it also calls `interrupt_check` -- if it returns
        True, then breaks from the loop and return.

        :param detected_callback: a function or list of functions. The number of
                                  items must match the number of models in
                                  `decoder_model`.
        :param interrupt_check: a function that returns True if the main loop
                                needs to stop.
        :param float sleep_time: how much time in second every loop waits.
        :return: None
        """
        if interrupt_check():
            logger.debug("detect voice return")
            return

        while True:
            if interrupt_check():
                logger.debug("detect voice break")
                break
            data = self.ring_buffer.get()
            if len(data) == 0:
                time.sleep(sleep_time)
                continue

            #ans = self.detector.RunDetection(data)
            if ans == -1:
                logger.warning("Error initializing streams or reading audio data")
            elif ans > 0:
                message = "Keyword " + str(ans) + " detected at time: "
                message += time.strftime("%Y-%m-%d %H:%M:%S",
                                         time.localtime(time.time()))
                logger.info(message)
                callback = detected_callback[ans - 1]
                if callback is not None:
                    callback()

        logger.debug("finished.")

    def terminate(self):
        """
        Terminate audio stream. Users cannot call start() again to detect.
        :return: None
        """
        self.stream_in.stop_stream()
        self.stream_in.close()
        self.audio.terminate()


#============================================

import pyowm

class weather_forecast(object):
    def __init__(self):
        self.owm = pyowm.OWM('9d91745bf01401fff530b18adf72dcb5')

    def start(self, location):

        # Will it be sunny tomorrow at this time in Milan (Italy) ?
        #forecast = self.owm.daily_forecast(location)
        #tomorrow = pyowm.timeutils.tomorrow()
        #forecast.will_be_sunny_at(tomorrow)  # Always True in Italy, right? ;-)

        # Search for current weather in London (UK)
        observation = self.owm.weather_at_place(location)
        w = observation.get_weather()
        print(w)                      # <Weather - reference time=2013-12-18 09:20,
        # Weather details
        w.get_wind()                  # {'speed': 4.6, 'deg': 330}
        w.get_humidity()              # 87
        w.get_temperature('celsius')  # {'temp_max': 10.5, 'temp': 9.7, 'temp_min': 9.0}

       # return (w._detailed_status + ', ' + )


def main():
    agent = VoiceAssistant(session_id='Room17', sample_rate=44100, chunk_size=4096, energy_threshold=300)
    weather = weather_forecast()
    while True:
        time.sleep(0.05)
        if len(agent.audio_instance.speech)>0:
            ai_return = agent.dialog(agent.audio_instance.speech, agent.audio_instance.audio)
            agent.speak(ai_return)
            agent.audio_instance.get()
          #  if (agent.ai_response_dict['Room17'][0]['action']=='weather'):
          #      #agent.speak(weather.start(agent.ai_response_dict['Room17'][0]['params']['address']['city']))
          #      pass

if __name__ == '__main__':
    main()



