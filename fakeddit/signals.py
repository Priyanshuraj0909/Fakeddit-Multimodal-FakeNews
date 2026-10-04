"""Descriptive text indicators, never a truth classifier."""
import re

PHRASES = ("you won't believe", "shocking", "secret", "they don't want you to know", "miracle", "guaranteed", "breaking")


def analyze(text: str) -> dict:
    words = re.findall(r"\b[\w'-]+\b", text)
    letters = [c for c in text if c.isalpha()]
    matches = [phrase for phrase in PHRASES if re.search(r"\b" + re.escape(phrase) + r"\b", text, re.IGNORECASE)]
    return {
        "mode": "descriptive",
        "verdict": "Not assessed",
        "word_count": len(words),
        "character_count": len(text),
        "uppercase_ratio": round(sum(c.isupper() for c in letters) / max(len(letters), 1), 3),
        "exclamation_count": text.count("!"),
        "phrases": matches,
        "links": len(re.findall(r"https?://[^\s]+", text)),
        "note": "Writing style cannot establish whether a claim is true. Verify the original source, date, evidence, and image context.",
    }
