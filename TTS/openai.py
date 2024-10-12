import os
import re
import requests
from pathlib import Path
from typing import Tuple
from openai import OpenAI
from rich.progress import track

from utils import settings
from utils.console import print_step, print_substep
from utils.voice import sanitize_text



class oai_TTSEngine:
    """OpenAI Text-to-Speech Engine Wrapper"""

    def __init__(self):
        self.reddit_object = None  # Initialize as None
        self.redditid = ""
        self.path = "assets/temp/"  # Default path
        self.max_length = 50  # Maximum audio length
        self.length = 0
        self.last_clip_length = 0
        # Initialize OpenAI client
        self.client = None

        self.initialize_client()
        # Set OpenAI API key
       # OpenAI.api_key = settings.config["settings"]["tts"]["openai_api_key"]

    def set_reddit_object(self, reddit_object: dict):
        """Set the reddit object for processing."""
        self.reddit_object = reddit_object
        self.redditid = re.sub(r"[^\w\s-]", "", reddit_object["thread_id"])
        self.path = os.path.join("assets/temp/", self.redditid, "mp3")

    def initialize_client(self):
        """Initialize the OpenAI client with the API key."""
        api_key = settings.config["settings"]["tts"].get("openai_api_key")
        if not api_key:
            raise ValueError("OpenAI API key is missing. Please check your configuration.")
        self.client = OpenAI(api_key=api_key)
    
    def run(self, text: str, filepath: str, random_voice: bool = False) -> None:
       
        if self.client is None:
            self.initialize()
       
        """Generate audio from text and save it to the specified file path."""
        
        
        self.generate_audio(text, filepath)

    def generate_audio(self, text: str, filepath: str):
        """Call OpenAI's TTS API to generate audio"""
        try:
            response = self.client.audio.speech.create(
                model="tts-1-hd",  # Ensure this model is valid according to the latest OpenAI API
                voice="alloy",
                input=text,
                response_format="mp3"  # Ensure this is the correct format as per the updated API documentation
            )

            audio_content = response.content  # Assume this field contains the binary audio data

            with open(filepath, 'wb') as out:
                out.write(audio_content)  # Write the audio content to the file
            print(f"Audio saved to {filepath}")

        except Exception as e:
            print(f"Error generating audio: {str(e)}")
            

    def get_audio_length(self, filepath: str) -> float:
        """Returns the duration of the audio file."""
        from mutagen.mp3 import MP3
        audio = MP3(filepath)
        return audio.info.length

def process_text(text: str, clean: bool = True):
    lang = settings.config["reddit"]["thread"]["post_lang"]
    new_text = sanitize_text(text) if clean else text
    if lang:
        print_substep("Translating Text...")
        translated_text = translators.translate_text(text, translator="google", to_language=lang)
        new_text = sanitize_text(translated_text)
    return new_text