"""CLI catalogs. Language is --lang, then ~/.superstep/cli.json, then LANG or LC_MESSAGES."""
from __future__ import annotations

import json
import os
from pathlib import Path


class Catalog:
    def __init__(self, lang: str, messages: dict[str, str]):
        self.lang = lang
        self.messages = messages

    def format(self, key: str, **kwargs: str) -> str:
        return self.messages[key].format(**kwargs)

    @classmethod
    def load(cls, lang: str) -> Catalog:
        path = Path(__file__).resolve().parent / "locales" / f"{lang}.json"
        messages = json.loads(path.read_text(encoding="utf-8"))
        return cls(lang, messages)


def lang_flag(argv: list[str]) -> str | None:
    """The --lang value, wherever it sits. Argparse would drop a parent flag when the subparser has its own default."""
    for index, arg in enumerate(argv):
        if arg == "--lang" and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    return None


def resolve_lang(flag: str | None) -> str:
    if flag in ("en", "vi"):
        return flag
    return _file_lang() or _env_lang()


def _file_lang() -> str | None:
    path = Path.home() / ".superstep" / "cli.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    lang = raw.get("lang") if isinstance(raw, dict) else None
    return lang if lang in ("en", "vi") else None


def _env_lang() -> str:
    for name in ("LANG", "LC_MESSAGES"):
        if os.environ.get(name, "").lower().startswith("vi"):
            return "vi"
    return "en"
