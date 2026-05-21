"""
This module gives our assistant its voice and ears.
It uses 'edge-tts' for speaking and 'Vosk' for listening to the user.
"""
import edge_tts
import vosk
import os
import json
import wave
from pydub import AudioSegment

class VoiceEngine:
    def __init__(self, model_path="/opt/vosk-model-en", voice="en-IN-NeerjaNeural"):
        """
        Initializes the voice settings and loads the speech recognition model.
        """
        self.voice = voice
        if not os.path.exists(model_path):
            print(f"Vosk model not found at {model_path}. STT will be unavailable.")
            self.stt_model = None
        else:
            self.stt_model = vosk.Model(model_path)

    async def text_to_speech(self, text, output_file="response.mp3"):
        """
        Generates a natural-sounding audio file from a string of text.
        """
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_file)
        return output_file

    def speech_to_text(self, audio_path):
        """
        Analyzes a pre-recorded audio file and extracts the spoken text.
        It converts the input to the required WAV format if necessary.
        """
        if not self.stt_model:
            return "STT model not loaded."
            

        
        try:
            audio = AudioSegment.from_file(audio_path)
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            temp_wav = "temp_stt.wav"
            audio.export(temp_wav, format="wav")
            
            wf = wave.open(temp_wav, "rb")
            rec = vosk.KaldiRecognizer(self.stt_model, wf.getframerate())
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    results.append(json.loads(rec.Result())["text"])
            
            results.append(json.loads(rec.FinalResult())["text"])
            
            # Cleanup
            wf.close()
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
                
            return " ".join([r for r in results if r])
        except Exception as e:
            print(f"Error processing audio: {e}")
            return None

    def live_listen(self, prompt="Listening..."):
        """
        Actively listens to the microphone and waits for the user to stop speaking
        before returning the recognized text.
        """
        import pyaudio
        if not self.stt_model:
            return "STT model not loaded."

        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
        stream.start_stream()

        print(prompt)
        rec = vosk.KaldiRecognizer(self.stt_model, 16000)
        
        try:
            while True:
                data = stream.read(4000, exception_on_overflow=False)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())["text"]
                    if result:
                        stream.stop_stream()
                        stream.close()
                        p.terminate()
                        return result
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
        return ""
