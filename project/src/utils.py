import re
import unicodedata


def normalize_text(text):
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_get(d, key, default=None):
    return d[key] if key in d else default