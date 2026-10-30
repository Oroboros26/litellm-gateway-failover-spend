"""Regex PII redaction. Limitation: regex only, misses names/addresses; swap in Presidio if recall matters."""
import re

PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,4})?\b"),
    "CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "PHONE": re.compile(r"\+?\d[\d ()-]{8,}\d"),
}


def redact(text: str) -> tuple[str, int]:
    n = 0
    for label, pat in PATTERNS.items():
        text, k = pat.subn(f"[{label}]", text)
        n += k
    return text, n


def redact_messages(messages: list[dict]) -> int:
    """Redact in place (str content and text parts). Returns number of hits."""
    hits = 0
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            m["content"], k = redact(c)
            hits += k
        elif isinstance(c, list):
            for part in c:
                if part.get("type") == "text":
                    part["text"], k = redact(part["text"])
                    hits += k
    return hits
