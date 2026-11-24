import json, os, ssl, urllib.request
import certifi
from dotenv import load_dotenv

load_dotenv()
CTX = ssl.create_default_context(cafile=certifi.where())
UA = {"User-Agent": "Mozilla/5.0"}


def get(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
        return json.load(r)


print("GROQ models (use as groq/<name>):")
try:
    data = get("https://api.groq.com/openai/v1/models",
               {"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"})
    for m in sorted(x["id"] for x in data["data"]):
        print("  groq/" + m)
except Exception as e:
    print("  error:", e)

print("\nGEMINI models (use as gemini/<name>):")
try:
    data = get("https://generativelanguage.googleapis.com/v1beta/models"
               f"?key={os.getenv('GEMINI_API_KEY')}&pageSize=200")
    for m in data["models"]:
        if "generateContent" in m.get("supportedGenerationMethods", []):
            print("  gemini/" + m["name"].split("/")[-1])
except Exception as e:
    print("  error:", e)