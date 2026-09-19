import json
import urllib.request

# PASTE YOUR FRESH OPENROUTER KEY HERE DIRECTLY INSIDE THE QUOTES,
# or (better) set OPENROUTER_API_KEY in .env — zoey.py / engine.py / api.py
# will load from there automatically.
import os
from dotenv import load_dotenv
load_dotenv(override=True)
API_KEY = (
    os.environ.get("OPENROUTER_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
    or ""
).strip().strip('"').strip("'")

# Clean any whitespace, newlines, or hidden quote marks
API_KEY = API_KEY.strip().strip('"').strip("'").replace("\ufeff", "")

url = "https://openrouter.ai/api/v1/chat/completions"
payload = json.dumps({
    "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "messages": [{"role": "user", "content": "Hello!"}]
}).encode("utf-8")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost",
    "X-Title": "ZOEY Assistant"
}

print("Testing direct raw HTTP connection to OpenRouter...")
req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode("utf-8"))
        print("\n🎉 SUCCESS! OpenRouter replied:")
        print(res["choices"][0]["message"]["content"])
except Exception as e:
    print("\n❌ Error:", e)