"""Public browser policy and the standalone runtime embedded in Python exports.

Generated files import nothing from Superstep. Tokens, proxy passwords and profile
state are not copied; the runtime reads them from the environment at execution time.
"""
from __future__ import annotations

import re

from .browser_contract import BrowserSettings

TS_BROWSER_REFUSAL = (
    "Browser tools are exported as Python. This TypeScript file refuses them "
    "instead of calling a silent MCP stub."
)

_ENV_SAFE = re.compile(r"[^A-Z0-9]+")


def alias_env(alias: str, kind: str) -> str:
    suffix = _ENV_SAFE.sub("_", alias.upper()).strip("_") or "BROWSER"
    return f"SUPERSTEP_BROWSER_{kind}_{suffix}"


def public_policy(raw) -> dict | None:
    """Allowlisted connection policy, or None when the stored settings are not a browser contract.

    Secret fields are not part of BrowserSettings. Proxy credentials and profile cookies are omitted.
    """
    try:
        settings = BrowserSettings.model_validate(raw or {})
    except Exception:
        return None
    proxy = {"mode": settings.proxy.mode, "server": settings.proxy.server, "auth": settings.proxy.auth}
    profile = None if settings.profile is None else {"name": settings.profile.name, "origins": list(settings.profile.origins)}
    return {
        "provider": settings.provider,
        "allowed_origins": list(settings.allowed_origins),
        "proxy": proxy,
        "profile": profile,
        "action_timeout_ms": settings.action_timeout_ms,
        "idle_timeout_s": settings.idle_timeout_s,
        "lifetime_s": settings.lifetime_s,
        "max_actions": settings.max_actions,
        "max_pages": settings.max_pages,
        "require_mutating_approval": settings.require_mutating_approval,
        "allow_evaluate_js": settings.allow_evaluate_js,
        "allow_upload": settings.allow_upload,
        "allow_download": settings.allow_download,
        "download_max_bytes": settings.download_max_bytes,
        "download_allowed_types": list(settings.download_allowed_types),
        "stealth": settings.stealth,
    }


def with_env(alias: str, policy: dict) -> dict:
    """Attach the environment variable names for this alias. Values are never included."""
    return {**policy, "env": {
        "token": alias_env(alias, "TOKEN"),
        "endpoint": alias_env(alias, "ENDPOINT"),
        "proxy_username": alias_env(alias, "PROXY_USERNAME"),
        "proxy_password": alias_env(alias, "PROXY_PASSWORD"),
        "proxy_url": alias_env(alias, "PROXY_URL"),
        "profile": alias_env(alias, "PROFILE"),
    }}


def export_binding(data) -> dict:
    """URL binding copied into the export. Model source has no fallback value."""
    if not isinstance(data, dict):
        return {"source": "model"}
    source = data.get("source") or "model"
    if source not in ("model", "fixed", "state"):
        return {"source": "model"}
    out = {"source": source}
    if source != "model" and isinstance(data.get("value"), str):
        out["value"] = data["value"]
    return out


# Inserted after `BROWSER_POLICY = ...`. Names `render` and `os` come from the exporter header.
# Keep this source free of triple-single-quotes. Regexes use double-quoted raw strings.
PY_RUNTIME = r'''
import importlib
import ipaddress
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit

_MUTATING = {"click", "fill", "upload", "download", "evaluate"}
_OBSERVED = {"click", "fill", "extract", "upload", "download", "evaluate"}
_sessions = {}
_guard = threading.Lock()


class BrowserError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class SessionLost(BrowserError):
    def __init__(self, message="session lost"):
        super().__init__("session_lost", message)


class UnknownEffect(BrowserError):
    def __init__(self, message="unknown effect"):
        super().__init__("unknown_effect", message)


class _Page:
    def __init__(self):
        self.url = ""
        self.html = ""
        self.generation = 0
        self.observation = None
        self.elements = []
        self.values = {}


class _Session:
    def __init__(self):
        self.lock = threading.Lock()
        self.seq = 0
        self.active = 0
        self.peak = 0
        self.page = _Page()
        now = time.monotonic()
        self.touched = now
        self.started = now
        self.actions = 0


class _DenyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BrowserError("whitelist_denied", "redirect is not followed")


def _env(name):
    if not isinstance(name, str) or not name:
        return ""
    return os.environ.get(name) or ""


def _driver():
    return (os.environ.get("SUPERSTEP_BROWSER_DRIVER") or "memory").strip().lower()


def _fault():
    # One-shot: a lost or unknown outcome is not retried by reading the same variable again.
    value = os.environ.get("SUPERSTEP_BROWSER_FAULT") or ""
    if value:
        os.environ.pop("SUPERSTEP_BROWSER_FAULT", None)
    return value.strip().lower()


def _approved(answer):
    if answer is True:
        return True
    return isinstance(answer, dict) and answer.get("approved") is True


def _public_args(arguments):
    if not isinstance(arguments, dict):
        return {}
    out = {}
    for key, value in arguments.items():
        if key in ("value", "script", "expression", "source_id"):
            out[key] = "[redacted]"
        elif key == "url" and isinstance(value, str):
            parts = urlsplit(value)
            out[key] = f"{parts.scheme}://{parts.hostname or ''}"
        else:
            out[key] = value
    return out


def browser_interrupt(alias, tool, arguments):
    # Lazy import so a memory-driver test can rebind browser_decide and stay offline.
    from langgraph.types import interrupt
    answer = interrupt({"browser": alias, "tool": tool, "arguments": _public_args(arguments)})
    return _approved(answer)


def browser_decide(alias, tool, arguments):
    return browser_interrupt(alias, tool, arguments)


def bind_browser_url(binding, arguments, state):
    if not isinstance(arguments, dict):
        arguments = {}
    source = (binding or {}).get("source") or "model"
    if source == "model":
        return arguments
    if "url" in arguments:
        raise BrowserError("override", "A bound URL cannot be overridden by model arguments")
    if source == "fixed":
        value = (binding or {}).get("value") or ""
    elif source == "state":
        value = render(str((binding or {}).get("value") or ""), state)
    else:
        return arguments
    if not isinstance(value, str) or not value.strip():
        raise BrowserError("missing_url", "Bound URL is missing")
    return {**arguments, "url": value}


def _select(target, state):
    field = (target or {}).get("observation_field") or ""
    result = state.get(field) if isinstance(state, dict) else None
    if not isinstance(result, dict) or result.get("status") != "confirmed":
        raise BrowserError("missing_target", "Browser recipe target is missing or ambiguous")
    observation = result.get("observation") or {}
    elements = observation.get("elements") or []
    role, text = target.get("role"), target.get("text")
    matches = [item for item in elements if item.get("role") == role and (text is None or item.get("text") == text)]
    if len(matches) != 1 or not observation.get("observation_id"):
        raise BrowserError("missing_target", "Browser recipe target is missing or ambiguous")
    return observation["observation_id"], matches[0]["element_id"]


def browser_prepare(tool, arguments, target, targets, state):
    arguments = dict(arguments or {})
    if tool in ("click", "fill") and isinstance(target, dict):
        observation, element = _select(target, state)
        arguments["observation_id"] = observation
        arguments["element_id"] = element
    elif tool == "extract" and isinstance(targets, dict):
        fields, observation = {}, None
        for name, item in targets.items():
            current, element = _select(item, state)
            if observation is not None and observation != current:
                raise BrowserError("stale_observation", "Browser recipe observation changed")
            observation, fields[name] = current, element
        arguments["observation_id"] = observation
        arguments["fields"] = fields
    return arguments


def _policy(alias):
    item = BROWSER_POLICY.get(alias) if isinstance(BROWSER_POLICY, dict) else None
    if not isinstance(item, dict):
        raise BrowserError("missing_policy", "No browser policy for this alias")
    return item


def _origin_of(url):
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise BrowserError("whitelist_denied", "URL scheme or userinfo is not allowed")
    if parts.scheme == "javascript":
        raise BrowserError("whitelist_denied", "javascript URLs are not allowed")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    host = parts.hostname.lower().rstrip(".")
    bracket = f"[{host}]" if ":" in host else host
    suffix = "" if (parts.scheme, port) in (("http", 80), ("https", 443)) else f":{port}"
    return f"{parts.scheme}://{bracket}{suffix}"


def _allowed(policy, url):
    origin = _origin_of(url)
    allowed = []
    for item in policy.get("allowed_origins") or []:
        try:
            allowed.append(_origin_of(item))
        except BrowserError:
            continue
    if origin not in allowed:
        raise BrowserError("whitelist_denied", "URL origin is not on the whitelist")
    return origin


def _private_host(host):
    if not host or host == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (not ip.is_global) or ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified


def _require_public(url):
    if _private_host(urlsplit(url).hostname or ""):
        raise BrowserError("private_address", "Playwright and Browserless refuse non-global addresses")


def _check_secrets(policy):
    env = policy.get("env") or {}
    if policy.get("provider") == "browserless":
        if not _env(env.get("endpoint")) or not _env(env.get("token")):
            raise BrowserError("token_missing", "Browserless endpoint and token must be set in the environment")
    proxy = policy.get("proxy") or {}
    if proxy.get("mode") == "custom" and proxy.get("auth") == "basic":
        if not _env(env.get("proxy_username")) or not _env(env.get("proxy_password")):
            raise BrowserError("proxy_credentials_missing", "Proxy username and password must be set in the environment")
    if policy.get("profile") and not _env(env.get("profile")):
        raise BrowserError("profile_missing", "profile state is not in the export; set " + str(env.get("profile") or "SUPERSTEP_BROWSER_PROFILE"))


def _attr(attrs, name):
    # Quote characters are chosen at run time. Patterns are normal strings so the exporter can embed them.
    for quote in ('"', "'"):
        pattern = "\\b" + re.escape(name) + "\\s*=\\s*" + quote
        pattern += "([^" + quote + "]*)" + quote
        match = re.search(pattern, attrs or "", re.I)
        if match:
            return match.group(1)
    return ""


def _clean(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _role(tag, attrs):
    if tag == "a":
        return "link"
    if tag == "button":
        return "button"
    if tag == "input":
        kind = (_attr(attrs, "type") or "text").lower()
        return "button" if kind in ("submit", "button") else "textbox"
    if tag == "textarea":
        return "textbox"
    if tag == "h1":
        return "heading"
    return "paragraph"


def _label(tag, attrs, inner):
    if tag == "input":
        return _attr(attrs, "aria-label") or _attr(attrs, "placeholder") or _attr(attrs, "value") or ""
    return _clean(inner)


def _elements(html):
    specs = (
        ("a", r"<a\b([^>]*)>(.*?)</a>"),
        ("button", r"<button\b([^>]*)>(.*?)</button>"),
        ("input", r"<input\b([^>]*)/?>"),
        ("textarea", r"<textarea\b([^>]*)>(.*?)</textarea>"),
        ("h1", r"<h1\b([^>]*)>(.*?)</h1>"),
        ("p", r"<p\b([^>]*)>(.*?)</p>"),
    )
    found = []
    for tag, pattern in specs:
        for match in re.finditer(pattern, html or "", re.I | re.S):
            attrs = match.group(1) or ""
            inner = match.group(2) if match.lastindex and match.lastindex >= 2 else ""
            role = _attr(attrs, "role") or _role(tag, attrs)
            found.append((match.start(), tag, attrs, role[:80], _label(tag, attrs, inner)[:1000]))
    found.sort(key=lambda item: item[0])
    elements = []
    for index, (pos, tag, attrs, role, text) in enumerate(found, 1):
        raw_id = _attr(attrs, "id")
        element_id = raw_id if re.fullmatch(r"[A-Za-z0-9_.:-]+", raw_id or "") else f"e{index}"
        elements.append({"element_id": element_id, "role": role, "text": text, "tag": tag, "href": _attr(attrs, "href")})
    return elements


def _title(html):
    match = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.I | re.S)
    return _clean(match.group(1)) if match else ""


def _body_text(html):
    match = re.search(r"<body[^>]*>(.*)</body>", html or "", re.I | re.S)
    return _clean(match.group(1) if match else html)


def _observation(page):
    origin = ""
    if page.url:
        try:
            origin = _origin_of(page.url)
        except BrowserError:
            origin = ""
    return {
        "observation_id": page.observation,
        "page_generation": page.generation,
        "origin": origin,
        "text": _body_text(page.html)[:16000],
        "elements": [{"element_id": item["element_id"], "role": item["role"], "text": item["text"]} for item in page.elements],
    }


def _ok(tool, seq, **extra):
    body = {"status": "confirmed", "operation": tool, "sequence": seq}
    body.update(extra)
    return body


def _http_get(url, policy):
    _allowed(policy, url)
    timeout = max(1, int((policy.get("action_timeout_ms") or 30000) / 1000))
    request = urllib.request.Request(url, headers={"User-Agent": "superstep-export-browser"})
    opener = urllib.request.build_opener(_DenyRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.read(200000).decode("utf-8", "replace")
    except BrowserError:
        raise
    except Exception:
        raise BrowserError("fetch_failed", "fetch failed") from None


def _proxy_for(policy):
    # Username and password are read here, at run time, and are not written into the file.
    proxy = policy.get("proxy") or {}
    if proxy.get("mode") != "custom" or not proxy.get("server"):
        return None
    if proxy.get("auth") != "basic":
        return {"server": proxy.get("server")}
    env = policy.get("env") or {}
    return {"server": proxy.get("server"), "username": _env(env.get("proxy_username")), "password": _env(env.get("proxy_password"))}


def _playwright_html(policy, url):
    try:
        sync_api = importlib.import_module("playwright.sync_api")
    except Exception:
        raise BrowserError("capability_refused", "playwright is not installed; install playwright and chromium, or set SUPERSTEP_BROWSER_DRIVER=memory") from None
    manager = sync_api.sync_playwright().start()
    browser = None
    try:
        browser = manager.chromium.launch(headless=True, proxy=_proxy_for(policy))
        page = browser.new_page()
        page.goto(url, timeout=int(policy.get("action_timeout_ms") or 30000))
        return page.content()
    finally:
        if browser is not None:
            browser.close()
        manager.stop()


def _browserless_html(policy, url):
    try:
        sync_api = importlib.import_module("playwright.sync_api")
    except Exception:
        raise BrowserError("capability_refused", "playwright is required for browserless connect_over_cdp") from None
    env = policy.get("env") or {}
    endpoint, token = _env(env.get("endpoint")), _env(env.get("token"))
    if not endpoint or not token:
        raise BrowserError("token_missing", "Browserless endpoint and token must be set in the environment")
    sep = "&" if "?" in endpoint else "?"
    manager = sync_api.sync_playwright().start()
    browser = None
    try:
        # The token stays in this process. It is not printed and it is not part of the generated source.
        browser = manager.chromium.connect_over_cdp(endpoint + sep + "token=" + token)
        page = browser.new_page()
        page.goto(url, timeout=int(policy.get("action_timeout_ms") or 30000))
        return page.content()
    finally:
        if browser is not None:
            browser.close()
        manager.stop()


def _fetch(policy, url):
    # Every driver honors the whitelist. Playwright and Browserless also refuse private hosts before launch.
    _allowed(policy, url)
    kind = _driver()
    if kind in ("playwright", "browserless"):
        _require_public(url)
        if kind == "playwright":
            return _playwright_html(policy, url)
        return _browserless_html(policy, url)
    if kind != "memory":
        raise BrowserError("capability_refused", "SUPERSTEP_BROWSER_DRIVER must be memory, playwright, or browserless")
    return _http_get(url, policy)


def _store(session, url, html, operation):
    page = _Page()
    page.url = url
    page.html = html
    page.generation = session.page.generation + 1
    page.elements = _elements(html)
    session.page = page
    session.actions += 1
    session.seq += 1
    page.observation = f"g{page.generation}-s{session.seq}"
    return _ok(operation, session.seq, url=url, observation=_observation(page))


def _fresh(session, arguments):
    observation = arguments.get("observation_id")
    if not isinstance(observation, str) or observation != session.page.observation:
        raise BrowserError("stale_observation", "observation_id does not match the current page")


def _element(session, element_id):
    for item in session.page.elements:
        if item.get("element_id") == element_id:
            return item
    raise BrowserError("missing_target", "element_id is not on the current page")


def _expire(session, policy):
    now = time.monotonic()
    life = float(policy.get("lifetime_s") or 0)
    idle = float(policy.get("idle_timeout_s") or 0)
    if life and now - session.started > life:
        session.page = _Page()
        raise SessionLost("lifetime exceeded")
    if idle and now - session.touched > idle:
        session.page = _Page()
        raise SessionLost("idle timeout")


def _command(session, policy, alias, tool, arguments):
    _expire(session, policy)
    fault = _fault()
    if fault == "lost":
        session.page = _Page()
        raise SessionLost("injected lost session")
    if fault == "unknown":
        raise UnknownEffect("injected unknown effect")
    if fault:
        raise BrowserError("capability_refused", "SUPERSTEP_BROWSER_FAULT must be empty, lost, or unknown")
    if tool in _MUTATING and policy.get("require_mutating_approval"):
        # browser_decide may return the raw interrupt answer. Only an explicit approval is a grant.
        if not _approved(browser_decide(alias, tool, arguments)):
            raise BrowserError("approval_rejected", "mutating browser action was not approved")
    if session.actions >= int(policy.get("max_actions") or 1):
        raise BrowserError("limit", "max_actions reached")
    if tool in _OBSERVED:
        _fresh(session, arguments)
    if tool in ("upload", "download"):
        flag = "allow_upload" if tool == "upload" else "allow_download"
        allowed = bool(policy.get(flag))
        raise BrowserError("capability_refused", f"{tool} is refused outside Studio; the connection allow flag is {allowed} but this runtime has no attachment store")
    if tool == "navigate":
        url = arguments.get("url")
        if not isinstance(url, str) or not url.strip() or url.strip().lower().startswith("javascript:"):
            raise BrowserError("missing_url" if not isinstance(url, str) or not url.strip() else "whitelist_denied", "navigate needs an http(s) url")
        return _store(session, url.strip(), _fetch(policy, url.strip()), "navigate")
    if tool == "snapshot":
        session.actions += 1
        session.seq += 1
        session.page.elements = _elements(session.page.html)
        session.page.observation = f"g{session.page.generation}-s{session.seq}"
        return _ok("snapshot", session.seq, observation=_observation(session.page))
    if tool == "screenshot":
        session.actions += 1
        session.seq += 1
        return _ok("screenshot", session.seq, captured=True, inline_bytes=False)
    if tool == "click":
        element = _element(session, arguments.get("element_id"))
        if element.get("href"):
            target = urljoin(session.page.url or "", element["href"])
            _allowed(policy, target)
            return _store(session, target, _fetch(policy, target), "click")
        session.actions += 1
        session.seq += 1
        return _ok("click", session.seq, clicked=element["element_id"])
    if tool == "fill":
        element = _element(session, arguments.get("element_id"))
        session.page.values[element["element_id"]] = arguments.get("value")
        session.actions += 1
        session.seq += 1
        return _ok("fill", session.seq, filled=True)
    if tool == "extract":
        fields = arguments.get("fields") or {}
        if not isinstance(fields, dict) or not fields:
            raise BrowserError("missing_target", "extract needs fields")
        extracted = {name: _element(session, element_id).get("text") or "" for name, element_id in fields.items()}
        session.actions += 1
        session.seq += 1
        return _ok("extract", session.seq, fields=extracted)
    if tool == "evaluate":
        if not policy.get("allow_evaluate_js"):
            raise BrowserError("capability_refused", "evaluate is disabled on this connection")
        expression = arguments.get("expression") or ""
        if expression == "document.title":
            value = _title(session.page.html)
        elif expression == "document.body.innerText":
            value = _body_text(session.page.html)
        else:
            raise BrowserError("capability_refused", "only document.title and document.body.innerText are allowed")
        session.actions += 1
        session.seq += 1
        return _ok("evaluate", session.seq, value=value)
    raise BrowserError("capability_refused", "unsupported browser tool " + str(tool))


def browser_call(alias, tool, arguments, state):
    # Model text and page text are data. They cannot replace the connection policy.
    if isinstance(state, dict) and state.get("__browser_policy__"):
        raise BrowserError("override", "page text and model state cannot change browser policy")
    policy = _policy(alias)
    _check_secrets(policy)
    with _guard:
        session = _sessions.get(alias)
        if session is None:
            session = _Session()
            _sessions[alias] = session
    with session.lock:
        session.active += 1
        session.peak = max(session.peak, session.active)
        try:
            return _command(session, policy, alias, str(tool or ""), arguments if isinstance(arguments, dict) else {})
        finally:
            session.active -= 1
            session.touched = time.monotonic()
'''

compile(PY_RUNTIME, "<browser-export>", "exec")
