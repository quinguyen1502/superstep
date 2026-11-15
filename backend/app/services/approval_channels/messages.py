"""Chat texts of approval requests, outcomes and identity codes in English and Vietnamese (catalogs in app/locales).

The request and the edited message follow the run owner's language (users.lang, set by the studio's language
switcher); a private answer to the person who pressed a button follows theirs. Unknown / unset: English.
"""
from typing import Optional

from ...engine.locale import LOCALES, catalog

LANGS = LOCALES
TEXTS: dict[str, dict[str, str]] = {lang: catalog(lang)["channels"] for lang in LANGS}  # app/locales/<lang>.json


def lang_of(user) -> str:
    """A user's chat language (None / unknown -> en)."""
    v = getattr(user, "lang", None)
    return v if v in LANGS else "en"


def text(lang: Optional[str], key: str, **kw) -> str:
    t = TEXTS.get(lang or "en", TEXTS["en"]).get(key) or TEXTS["en"].get(key) or key
    return t.format(**kw) if kw else t


def opinion_text(lang: Optional[str], r: Optional[dict]) -> Optional[str]:
    """The AI review's opinion as one line of an approval message, or None without one."""
    if not r or r.get("decision") not in ("approve", "reject", "escalate"): return None
    c = r.get("confidence")
    return text(lang, "ai_opinion", decision=text(lang, f"ai_{r['decision']}"), confidence="-" if c is None else f"{c:.2f}", reason=r.get("reason") or "").strip()
