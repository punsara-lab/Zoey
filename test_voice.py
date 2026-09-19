import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv("ELEVENLABS_API_KEY", "")
voice_id = os.getenv("ELEVENLABS_VOICE_ID", "tnSpp4vdxKPjI9w0GnoV")

print("\n--- ELEVENLABS VOICE TEST ---")
print(f"API Key: {api_key[:8]}... (Length: {len(api_key)})")
print(f"Voice ID: {voice_id}")

if not api_key:
    print("❌ ERROR: ELEVENLABS_API_KEY is missing from .env!")
    exit()

url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
headers = {
    "xi-api-key": api_key,
    "Content-Type": "application/json",
    "Accept": "audio/mpeg",
}
payload = {
    "text": "Hello! I am Zoey. Voice test completed successfully.",
    "model_id": "eleven_flash_v2_5",
    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
}

try:
    print("Requesting audio from ElevenLabs...")
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    
    if res.status_code == 200:
        print("🎉 SUCCESS: ElevenLabs generated audio!")
        with open("test_output.mp3", "wb") as f:
            f.write(res.content)
        print("Saved to test_output.mp3.")
        
        # Try playing audio using default Windows player
        os.system("start test_output.mp3")
    else:
        print(f"❌ ElevenLabs API Error {res.status_code}:", res.text)
except Exception as e:
    print("❌ Connection error:", e)