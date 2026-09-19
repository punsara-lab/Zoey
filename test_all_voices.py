import os
import time
import requests
import tempfile
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv("ELEVENLABS_API_KEY", "")

if not api_key:
    print("❌ ERROR: ELEVENLABS_API_KEY is missing from .env!")
    exit()

# Default premade female voices that work on ElevenLabs Free Tier
FEMALE_VOICES = {
    "Sarah": "EXAVITQu4vr4xnSDxMaL",    # Soft, young, approachable
    "Lily": "pFZP5JQG7iQjIQuC4Bku",     # Warm, British
    "Alice": "Xb7hH8MSUJpSbSDYk0k2",    # Confident, clear
    "Matilda": "XrExE9yKIg1WjnnlVkGX",  # Warm, friendly, young
    "Gigi": "jBpfuIE2acCO8z3wKNLl",     # Youthful, upbeat
    "Serena": "pMsXgVXv3BLzUgSXRplE",   # Expressive, calm
    "Mimi": "zrHiDhphv9ZnVXBqCLjz",     # Cute, energetic
}

def play_audio(file_path):
    """Play audio file using pygame or system fallback."""
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.quit()
    except Exception:
        # System default player fallback
        os.system(f'start "" "{file_path}"')
        time.sleep(3)

print("\n--- TESTING ALL DEFAULT FEMALE VOICES ---")

for name, voice_id in FEMALE_VOICES.items():
    print(f"\n🔊 Generating sample for: {name} (ID: {voice_id})...")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": f"Hello! I am {name}. How do I sound as your assistant Zoey?",
        "model_id": "eleven_flash_v2_5",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(res.content)
                temp_path = f.name

            print(f"▶️ Playing {name}'s voice...")
            play_audio(temp_path)

            try:
                os.remove(temp_path)
            except OSError:
                pass
        else:
            print(f"❌ Could not load {name}: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Error testing {name}: {e}")

    time.sleep(1)

print("\n🎉 Voice audition complete! Pick your favorite voice ID and save it to .env.")