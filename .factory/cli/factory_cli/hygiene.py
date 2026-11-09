"""Repository hygiene checks run by ``factory validate``.

Two project-wide rules keep the factory artifact store separate from the
product it describes:

* Artifact isolation. Product files (source, tests, scripts, examples,
  product docs) must not mention factory artifact IDs such as ``TASK-0001``
  or the ``.factory-state/`` store path. The store itself and the
  factory-managed instruction surfaces may reference artifacts freely.
* English only. Vietnamese text is allowed only in i18n surfaces: locale and
  translation catalogs and Vietnamese editions of docs. Everywhere else,
  including ``.factory-state/`` artifacts, it is an error.

Pull request text cannot be seen from a working tree, so :func:`pr_text_problems`
checks a title and body separately; ``factory pr check`` and ``factory
validate`` (when ``GITHUB_EVENT_PATH`` holds a pull request event) use it.

Projects can extend the defaults in ``.factory-state/hygiene.yaml``::

    i18n_paths:                 # Vietnamese allowed here
      - "frontend/e2e/fixtures/vi-*"
    artifact_reference_paths:   # artifact IDs and store paths allowed here
      - "docs/factory-notes.md"
    skip_paths:                 # not scanned at all
      - "third_party/*"
    allowed_terms:              # proper names that keep their diacritics
      - "Example Name"

Patterns are matched with :func:`fnmatch.fnmatchcase` against the
POSIX path relative to the project root; ``*`` also crosses ``/``.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import yaml

from .constants import FACTORY_STATE_DIR

HYGIENE_CONFIG_PATH = f"{FACTORY_STATE_DIR}/hygiene.yaml"

# Official artifact type prefixes (docs/artifact-model.md, docs/conventions.md,
# docs/clarifications.md). Product-specific prefixes are deliberately absent.
ARTIFACT_TYPES = (
    "REQ",
    "DISC",
    "PLAN",
    "DES",
    "ARCH",
    "TASK",
    "REV",
    "QA",
    "DEC",
    "SUM",
    "CLAR",
)

# IDs are zero-padded to four digits; three is the floor so short, unrelated
# tokens such as `QA-1` are not reported.
ARTIFACT_ID_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])(?:" + "|".join(ARTIFACT_TYPES) + r")-\d{3,}(?![A-Za-z0-9_])"
)
FACTORY_STATE_PATTERN = re.compile(r"\.factory-state(?![A-Za-z0-9_-])")

# Letters that only Vietnamese uses among Latin-script languages: breve a,
# horn o/u, stroked d, and the precomposed tone-marked vowels of Latin
# Extended Additional (U+1EA0..U+1EF9). Text is NFC-normalized first, so
# decomposed combining tone marks land in this range too.
_VI_STRONG = "\u0103\u0102\u01a1\u01a0\u01b0\u01af\u0111\u0110"
_VI_STRONG_PATTERN = re.compile("[" + _VI_STRONG + "\u1ea0-\u1ef9]")
# Circumflex vowels are shared with French and Portuguese; they count only
# alongside a tone-marked vowel on the same line and when the line has no
# letter Vietnamese never uses (cedilla, diaeresis, ring, n-tilde, ...).
_VI_WEAK_PATTERN = re.compile("[\u00e2\u00c2\u00ea\u00ca\u00f4\u00d4]")
_VI_TONE_PATTERN = re.compile(
    "[\u00e0\u00e1\u00e3\u00e8\u00e9\u00ec\u00ed\u00f2\u00f3\u00f5\u00f9\u00fa\u00fd"
    "\u00c0\u00c1\u00c3\u00c8\u00c9\u00cc\u00cd\u00d2\u00d3\u00d5\u00d9\u00da\u00dd]"
)
_NON_VI_LETTERS = re.compile(
    "[\u00e7\u00c7\u00eb\u00cb\u00ef\u00cf\u00fc\u00dc\u00f6\u00d6\u00e4\u00c4"
    "\u00f1\u00d1\u0153\u0152\u00e6\u00c6\u00ee\u00ce\u00fb\u00db\u00e5\u00c5"
    "\u00f8\u00d8\u00df]"
)

# Factory-managed instruction surfaces written by `factory init`, `factory
# import`, `factory tools apply`, and `factory skills apply`. They are not
# product code, so they may reference artifacts and the store path.
FACTORY_SURFACE_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".cursorrules",
    "project.md",
    "project-specs.md",
    "vision.md",
    "roadmap.md",
    ".gitmodules",
    ".github/pull_request_template.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
)
FACTORY_SURFACE_DIRS = (
    FACTORY_STATE_DIR,
    ".agents",
    ".claude",
    ".codex",
    ".cursor",
    ".grok",
    ".github/PULL_REQUEST_TEMPLATE",
)

# Never scanned: the framework copy or submodule (validated in its own
# repository), VCS metadata, dependency, build, and cache directories.
SKIP_DIR_NAMES = frozenset(
    {
        ".factory",
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "bower_components",
        "vendor",
        "third_party",
        "dist",
        "build",
        "out",
        "target",
        "coverage",
        "htmlcov",
        ".venv",
        "venv",
        "__pycache__",
        "site-packages",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".next",
        ".nuxt",
        ".svelte-kit",
        ".turbo",
        ".parcel-cache",
        ".cache",
        ".gradle",
        ".dart_tool",
        "Pods",
        ".terraform",
        ".idea",
        ".vscode",
    }
)
SKIP_FILE_NAMES = frozenset(
    {
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lockb",
        "poetry.lock",
        "uv.lock",
        "Pipfile.lock",
        "Cargo.lock",
        "Gemfile.lock",
        "composer.lock",
        "go.sum",
        "pubspec.lock",
        "Podfile.lock",
    }
)
SKIP_SUFFIXES = (".min.js", ".min.css", ".map", ".snap")
MAX_SCAN_BYTES = 1024 * 1024

# i18n surfaces where Vietnamese is allowed.
I18N_DIR_NAMES = frozenset(
    {"locales", "locale", "i18n", "l10n", "translations", "translation", "lang", "langs"}
)
I18N_NAME_TOKENS = I18N_DIR_NAMES
VI_LOCALE_TAGS = frozenset({"vi", "vi-vn", "vi_vn"})
I18N_SUFFIXES = (".po", ".pot", ".xliff", ".xlf", ".arb", ".strings", ".stringsdict")
_VI_NAME_SUFFIX = re.compile(r"[_-]vi(?:[_-]vn)?$", re.IGNORECASE)
_ANDROID_VI_DIR = re.compile(r"^values-vi(?:-r?vn)?$", re.IGNORECASE)

# Legal and attribution files carry people's names verbatim.
LANGUAGE_EXEMPT_NAME_PREFIXES = ("license", "licence", "copying", "notice", "authors", "contributors")
# A language's own name is how language switchers label it.
LANGUAGE_ENDONYMS = ("Ti\u1ebfng Vi\u1ec7t",)

# Ignore and attribute files may name the store path (for example to keep
# `.factory-state/` out of a container image) but not artifact IDs.
STORE_PATH_ALLOWED_NAMES = frozenset(
    {
        ".gitignore",
        ".gitattributes",
        ".dockerignore",
        ".npmignore",
        ".prettierignore",
        ".eslintignore",
        ".helmignore",
        ".vercelignore",
        ".gcloudignore",
        ".slugignore",
    }
)

_MAX_HITS_PER_FILE = 3


@dataclass
class HygieneConfig:
    i18n_paths: List[str] = field(default_factory=list)
    artifact_reference_paths: List[str] = field(default_factory=list)
    skip_paths: List[str] = field(default_factory=list)
    allowed_terms: List[str] = field(default_factory=list)

    @classmethod
    def load(cls, project_dir: Path) -> "HygieneConfig":
        path = project_dir / HYGIENE_CONFIG_PATH
        if not path.exists():
            return cls()
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ValueError(f"invalid {HYGIENE_CONFIG_PATH}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"{HYGIENE_CONFIG_PATH} must be a YAML mapping")
        known = {"i18n_paths", "artifact_reference_paths", "skip_paths", "allowed_terms"}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(
                f"{HYGIENE_CONFIG_PATH} has unknown keys: {', '.join(unknown)}"
            )
        values: Dict[str, List[str]] = {}
        for key in known:
            raw = data.get(key) or []
            if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
                raise ValueError(f"{HYGIENE_CONFIG_PATH}: {key} must be a list of strings")
            if key == "allowed_terms":
                values[key] = [item.strip() for item in raw if item.strip()]
            else:
                values[key] = [_normalize_pattern(item) for item in raw]
        return cls(**values)


def _normalize_pattern(pattern: str) -> str:
    pattern = pattern.strip()
    while pattern.startswith("./"):
        pattern = pattern[2:]
    return pattern


def _matches_any(relpath: str, patterns: Sequence[str]) -> bool:
    for pattern in patterns:
        if not pattern:
            continue
        if fnmatch.fnmatchcase(relpath, pattern):
            return True
        if pattern.endswith("/") and relpath.startswith(pattern):
            return True
        if not any(ch in pattern for ch in "*?[") and (
            relpath == pattern.rstrip("/") or relpath.startswith(pattern.rstrip("/") + "/")
        ):
            return True
    return False


def is_skipped_path(relpath: str) -> bool:
    parts = relpath.split("/")
    if any(part in SKIP_DIR_NAMES for part in parts[:-1]):
        return True
    name = parts[-1]
    if name in SKIP_FILE_NAMES:
        return True
    return name.endswith(SKIP_SUFFIXES)


def is_factory_surface(relpath: str) -> bool:
    if relpath in FACTORY_SURFACE_FILES:
        return True
    return any(relpath == root or relpath.startswith(root + "/") for root in FACTORY_SURFACE_DIRS)


def is_i18n_path(relpath: str) -> bool:
    """Locale catalogs and Vietnamese editions of docs (default allowlist)."""
    parts = relpath.split("/")
    for part in parts[:-1]:
        lowered = part.lower()
        if lowered in I18N_DIR_NAMES or lowered in VI_LOCALE_TAGS:
            return True
        if _ANDROID_VI_DIR.match(part):
            return True
    name = parts[-1]
    lowered = name.lower()
    if lowered.endswith(I18N_SUFFIXES):
        return True
    tokens = lowered.split(".")
    stems = tokens[:-1] if len(tokens) > 1 else tokens
    if any(token in VI_LOCALE_TAGS or token in I18N_NAME_TOKENS for token in stems):
        return True
    return any(_VI_NAME_SUFFIX.search(token) for token in stems)


def is_language_exempt(relpath: str) -> bool:
    name = relpath.rsplit("/", 1)[-1].lower()
    return name.startswith(LANGUAGE_EXEMPT_NAME_PREFIXES)


def _terms_pattern(terms: Sequence[str]) -> "re.Pattern[str]":
    names = [unicodedata.normalize("NFC", term) for term in (*LANGUAGE_ENDONYMS, *terms) if term]
    names.sort(key=len, reverse=True)
    return re.compile("|".join(re.escape(name) for name in names), re.IGNORECASE)


_DEFAULT_TERMS = _terms_pattern(())


def line_has_vietnamese(line: str, terms: Optional["re.Pattern[str]"] = None) -> bool:
    """True when ``line`` holds Vietnamese text after removing allowed terms."""
    text = (terms or _DEFAULT_TERMS).sub("", unicodedata.normalize("NFC", line))
    if _VI_STRONG_PATTERN.search(text):
        return True
    return bool(
        _VI_WEAK_PATTERN.search(text)
        and _VI_TONE_PATTERN.search(text)
        and not _NON_VI_LETTERS.search(text)
    )


def vietnamese_lines(
    text: str, terms: Optional["re.Pattern[str]"] = None
) -> List[Tuple[int, str]]:
    return [
        (number, line)
        for number, line in enumerate(text.splitlines(), start=1)
        if line_has_vietnamese(line, terms)
    ]


def artifact_references(text: str, include_store_path: bool = True) -> List[Tuple[int, str]]:
    hits: List[Tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in ARTIFACT_ID_PATTERN.finditer(line):
            hits.append((number, match.group(0)))
        if not include_store_path:
            continue
        for match in FACTORY_STATE_PATTERN.finditer(line):
            hits.append((number, match.group(0)))
    return hits


def _git_files(project_dir: Path) -> Optional[List[str]]:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(project_dir),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    toplevel = subprocess.run(
        ["git", "-C", str(project_dir), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if toplevel.returncode != 0 or Path(toplevel.stdout.strip()).resolve() != project_dir.resolve():
        # A project nested inside another repository: walk it directly.
        return None
    names = [name for name in result.stdout.decode("utf-8", "replace").split("\0") if name]
    return sorted(set(names))


def _walk_files(project_dir: Path) -> List[str]:
    files: List[str] = []
    for root, dirs, names in os.walk(project_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIR_NAMES)
        for name in sorted(names):
            files.append(Path(root, name).relative_to(project_dir).as_posix())
    return files


def project_files(project_dir: Path) -> List[str]:
    """Tracked and untracked, non-ignored files; falls back to a directory walk."""
    files = _git_files(project_dir)
    if files is None:
        files = _walk_files(project_dir)
    return [name for name in files if not is_skipped_path(name)]


def _read_text(path: Path) -> Optional[str]:
    try:
        if not path.is_file() or path.is_symlink():
            return None
        if path.stat().st_size > MAX_SCAN_BYTES:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw[:8192]:
        return None
    return raw.decode("utf-8", "replace")


def _format_hits(relpath: str, hits: List[Tuple[int, str]], message: str) -> str:
    shown = ", ".join(f"line {number}: {token}" for number, token in hits[:_MAX_HITS_PER_FILE])
    extra = len(hits) - _MAX_HITS_PER_FILE
    suffix = f" (+{extra} more)" if extra > 0 else ""
    return f"{message}: {relpath} ({shown}){suffix}"


def _snippet(line: str, limit: int = 60) -> str:
    text = line.strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def hygiene_problems(
    project_dir: Path,
    *,
    artifacts: bool = True,
    language: bool = True,
    pull_request: bool = True,
) -> Tuple[List[str], List[str]]:
    """Artifact-isolation and language errors for ``project_dir``.

    ``pull_request`` also checks the PR title and body when
    ``GITHUB_EVENT_PATH`` points at a pull request event.
    """
    errors: List[str] = []
    warnings: List[str] = []
    try:
        config = HygieneConfig.load(project_dir)
    except ValueError as exc:
        return [str(exc)], warnings
    terms = _terms_pattern(config.allowed_terms)
    for relpath in project_files(project_dir):
        if _matches_any(relpath, config.skip_paths):
            continue
        check_refs = (
            artifacts
            and not is_factory_surface(relpath)
            and not _matches_any(relpath, config.artifact_reference_paths)
        )
        check_language = (
            language
            and not is_i18n_path(relpath)
            and not is_language_exempt(relpath)
            and not _matches_any(relpath, config.i18n_paths)
        )
        if not (check_refs or check_language):
            continue
        text = _read_text(project_dir / relpath)
        if text is None:
            continue
        if check_refs:
            refs = artifact_references(
                text,
                include_store_path=relpath.rsplit("/", 1)[-1] not in STORE_PATH_ALLOWED_NAMES,
            )
            if refs:
                errors.append(
                    _format_hits(
                        relpath,
                        refs,
                        "product file references factory artifacts "
                        "(keep IDs and store paths in .factory-state/ and PR text)",
                    )
                )
        if check_language:
            lines = vietnamese_lines(text, terms)
            if lines:
                errors.append(
                    _format_hits(
                        relpath,
                        [(number, repr(_snippet(line))) for number, line in lines],
                        "Vietnamese text outside i18n surfaces (write it in English)",
                    )
                )
    if pull_request:
        errors.extend(github_event_pr_problems())
    return errors, warnings


def pr_text_problems(title: str, body: str) -> List[str]:
    problems: List[str] = []
    for label, text in (("title", title or ""), ("body", body or "")):
        lines = vietnamese_lines(text)
        if lines:
            problems.append(
                _format_hits(
                    f"pull request {label}",
                    [(number, repr(_snippet(line))) for number, line in lines],
                    "Vietnamese text in pull request (write PR text in English)",
                )
            )
    return problems


def load_pr_event(event_path: Path) -> Optional[Tuple[str, str]]:
    """Return ``(title, body)`` from a GitHub event payload, if it is a PR event."""
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    pull = payload.get("pull_request")
    if not isinstance(pull, dict):
        return None
    return str(pull.get("title") or ""), str(pull.get("body") or "")


def github_event_pr_problems(env: Optional[Dict[str, str]] = None) -> List[str]:
    environment = os.environ if env is None else env
    event_path = environment.get("GITHUB_EVENT_PATH")
    if not event_path:
        return []
    event = load_pr_event(Path(event_path))
    if event is None:
        return []
    return pr_text_problems(*event)
