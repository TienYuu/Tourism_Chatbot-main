import re
import unicodedata
import json

def normalize_text(text):
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_get(d, key, default=None):
    return d[key] if key in d else default

def safe_json_load(raw_text):

    try:

        return json.loads(raw_text)

    except Exception:

        # fallback nếu LLM trả markdown
        raw_text = raw_text.replace("```json", "")
        raw_text = raw_text.replace("```", "")

        return json.loads(raw_text)