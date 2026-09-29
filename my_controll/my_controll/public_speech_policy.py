import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from audio_common_msgs.msg import AudioData
from typing import Optional
import io
import wave
import numpy as np
import time
from piper.voice import PiperVoice

VOICE_PROFILES = {
   "adult": {
      "model_path": "/home/citic_lab/emdb_ws/src/my_controll/voices/en_US-lessac-medium.onnx",
      "config_path": None,
      "pitch_shift": 0,
   },
   "kid": {
       "model_path": "/home/citic_lab/emdb_ws/src/my_controll/voices/en_US-amy-medium.onnx",
       "config_path": None,       
       "pitch_shift": 6,
   },
   "funny_man": {
      "model_path": "/home/citic_lab/emdb_ws/src/my_controll/voices/en_US-danny-low.onnx",
      "config_path": None,
      "pitch_shift": -2,
   },
}

DEFAULT_VOICE = "adult"


def pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int, channels=1, sampwidth=2):
   buf = io.BytesIO()
   with wave.open(buf, "wb") as wf:
       wf.setnchannels(channels)
       wf.setsampwidth(sampwidth)
       wf.setframerate(sample_rate)
       wf.writeframes(pcm_bytes)
   return buf.getvalue()


class TextToSpeechNode(Node):

   def __init__(self):
      super().__init__("text_to_speech_node")
      self.declare_parameter("active_voice", DEFAULT_VOICE)
      self.publisher_ = self.create_publisher(AudioData, "/audio_out/raw", 0)
      self.subscription_ = self.create_subscription(String, "/tts/input", self._on_text, 0)
      self._voices = {}
      for name, cfg in VOICE_PROFILES.items():
         self._voices[name] = PiperVoice.load(
            cfg["model_path"],
            config_path=cfg["config_path"] or (cfg["model_path"] + ".json"),
            use_cuda=False,
         )

   def _active_voice(self):
      return self.get_parameter("active_voice").value

   def _on_text(self, msg):
      self.call_speech(msg.data)

   def call_speech(self, text: str, voice_name: Optional[str] = None):
      voice_name = voice_name or self._active_voice()
      if voice_name not in self._voices:
         voice_name = DEFAULT_VOICE
      
      audio = self._tts(text, voice_name)

      if audio:
         msg = AudioData()
         msg.data = audio
         self.publisher_.publish(msg)

   def _tts(self, text: str, voice_name: str):
      voice = self._voices[voice_name]
      #profile = VOICE_PROFILES[voice_name]
      voice.config.length_scale = 1.4

      sample_rate = getattr(voice.config, "sample_rate", 22050)

      try:
         chunks = voice.synthesize(text)
         pcm_parts = []
         for chunk in chunks:
               if hasattr(chunk, "audio_int16_bytes"):
                  pcm_parts.append(chunk.audio_int16_bytes)
               elif hasattr(chunk, "audio"):
                  arr = np.asarray(chunk.audio, dtype=np.int16)
                  pcm_parts.append(arr.tobytes())
               else:
                  raise TypeError(f"Unknown chunk type: {type(chunk)}")

         pcm = b"".join(pcm_parts)
         wav = pcm_to_wav_bytes(pcm, sample_rate)
         return list(wav)

      except Exception as e:
         self.get_logger().error(f"Synthesis error: {e}")
         return None


def main():
   rclpy.init()
   node = TextToSpeechNode()

   # node.call_speech("Hello, I am robot Tiago speaking clearly for adults.", "adult")
   # #rclpy.spin(node)
   # time.sleep(10)
   node.call_speech("Hello people", "kid")
   node.destroy_node()
   rclpy.shutdown()

if __name__ == "__main__":
   main()



# import rclpy
# from rclpy.node import Node
# from audio_common_msgs.msg import AudioData
# from gtts import gTTS
# from pydub import AudioSegment
# import io

# class TextToSpeechNode(Node):
#    def __init__(self):
#       super().__init__('text_to_speech_node')
#       self.publisher_ = self.create_publisher(AudioData, '/audio_out/raw', 0)
#       #self.timer = self.create_timer(5.0, self.call_speech)  # Publikuj každých 5 sekund

#    def call_speech(self, input_text):
#       text = input_text
#       audio_data = self.text_to_speech(text)
#       if audio_data:
#          msg = AudioData()
#          msg.data = audio_data
#          self.publisher_.publish(msg)
#          self.get_logger().info('Publishing audio data.')

#    def text_to_speech(self, text):
#       try:
#          tts = gTTS(text=text, lang='en')
#          audio_buffer = io.BytesIO()
#          tts.write_to_fp(audio_buffer)
#          audio_buffer.seek(0)
#          audio = AudioSegment.from_file(audio_buffer, format="mp3")
#          wav_buffer = io.BytesIO()
#          audio.export(wav_buffer, format="wav")
#          wav_buffer.seek(0)
#          return list(wav_buffer.getvalue())
      
#       except Exception as e:
#          self.get_logger().error(f'Error in transfer to speech: {e}')
#          return None
      
# def main(args=None):
#    rclpy.init(args=args)
#    node = TextToSpeechNode()
#    node.call_speech("Hello, I am Tiago. I would like to see that you take full attention.")
#    node.destroy_node()
#    rclpy.shutdown()

# if __name__ == '__main__':
#    main()