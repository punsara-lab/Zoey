import json
import urllib.request

# PASTE YOUR FRESH OPENROUTER KEY HERE DIRECTLY INSIDE THE QUOTES:
API_KEY = "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"

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