"""The language of offline answers (the mock model and the example tools): en (default) or vi.
The studio sends its UI language with run and chat requests; Accept-Language is the fallback."""
from typing import Optional

LOCALES = ("en", "vi")
DEFAULT = "en"


def pick(*candidates: Optional[str]) -> str:
    """The first supported language in an explicit value or an Accept-Language header ("vi-VN,vi;q=0.9"), else en."""
    for c in candidates:
        if not isinstance(c, str): continue
        for part in c.split(","):
            tag = part.split(";")[0].strip().lower().split("-")[0]
            if tag in LOCALES: return tag
    return DEFAULT
