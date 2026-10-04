import re
import unicodedata

_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w-])")
_PAN = re.compile(r"(?<![A-Z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Z0-9])", re.IGNORECASE)
_AADHAAR = re.compile(r"(?<![+\d])(?:\d[ -]?){11}\d(?!\d)")
_INDIAN_PHONE = re.compile(r"(?<!\w)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\w)")
_WHITESPACE = re.compile(r"\s+")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def normalize_and_redact(content: str) -> str:
    normalized = unicodedata.normalize("NFC", content)
    normalized = _CONTROL_CHARS.sub(" ", normalized)
    normalized = _WHITESPACE.sub(" ", normalized).strip()

    for pattern, label in (
        (_EMAIL, "EMAIL"),
        (_PAN, "PAN"),
        (_INDIAN_PHONE, "PHONE"),
        (_AADHAAR, "AADHAAR"),
    ):
        normalized = pattern.sub(f"[REDACTED {label}]", normalized)

    return normalized
