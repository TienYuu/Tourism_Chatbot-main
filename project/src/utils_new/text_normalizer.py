# utils/text_normalizer.py

import re
import unicodedata


def remove_accents(text: str) -> str:
    """
    Remove Vietnamese accents.
    """
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        c for c in text
        if unicodedata.category(c) != "Mn"
    )
    return unicodedata.normalize("NFC", text)


def normalize_text(text: str) -> str:
    """
    Normalize text for entity matching.
    """

    text = text.lower()

    # remove accents
    text = remove_accents(text)

    # replace special chars
    text = re.sub(r"[-_/]", " ", text)

    # remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)

    # collapse spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text