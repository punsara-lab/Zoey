import os
from dotenv import load_dotenv

load_dotenv()

# Check for both possible key names
key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

print("\n--- OPENROUTER KEY DIAGNOSTIC ---")
if not key:
    print("❌ RESULT: No API key found! Python cannot see your .env file.")
else:
    masked_key = key[:10] + "..." + key[-4:] if len(key) > 14 else "INVALID_LENGTH"
    print(f"✅ Key loaded: {masked_key} (Length: {len(key)})")
    
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    
    try:
        res = client.chat.completions.create(
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            messages=[{"role": "user", "content": "Hello!"}],
        )
        print("🎉 SUCCESS! OpenRouter connected successfully.")
        print("Response:", res.choices[0].message.content)
    except Exception as e:
        print("❌ API REJECTED KEY:", e)