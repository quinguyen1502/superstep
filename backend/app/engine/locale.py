"""The language of offline answers (the mock model and the example tools): en (default) or vi.
The studio sends its UI language with run and chat requests; Accept-Language is the fallback.

Server-side texts in each language live in the catalogs `app/locales/<lang>.json`; `text` and `by_locale` read them."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

LOCALES = ("en", "vi")
DEFAULT = "en"
CATALOG_DIR = Path(__file__).resolve().parent.parent / "locales"


def pick(*candidates: Optional[str]) -> str:
    """The first supported language in an explicit value or an Accept-Language header ("vi-VN,vi;q=0.9"), else en."""
    for c in candidates:
        if not isinstance(c, str): continue
        for part in c.split(","):
            tag = part.split(";")[0].strip().lower().split("-")[0]
            if tag in LOCALES: return tag
    return DEFAULT


@lru_cache(maxsize=None)
def catalog(lang: str) -> Dict[str, Any]:
    """The whole catalog of one language (`app/locales/<lang>.json`)."""
    return json.loads((CATALOG_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def text(lang: Optional[str], key: str) -> Any:
    """The value at a dotted key ("tools.no_order") in `lang`'s catalog; English when the language or key is missing."""
    for candidate in (lang if lang in LOCALES else DEFAULT, DEFAULT):
        node: Any = catalog(candidate)
        for part in key.split("."):
            node = node.get(part) if isinstance(node, dict) else None
            if node is None: break
        if node is not None: return node
    raise KeyError(key)


def by_locale(key: str) -> Dict[str, Any]:
    """{lang: value} for a dotted key, for every supported language."""
    return {lang: text(lang, key) for lang in LOCALES}
