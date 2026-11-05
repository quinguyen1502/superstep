"""Pure login-state checks, shared by trusted service, supervisor and remote controller."""
import json
import time
from urllib.parse import urlsplit

from .browser_contract import BrowserSettings, ProfileSeed, ProfileState
from .browser_network import DestinationPolicy


class ProfileDenied(Exception):
    def __init__(self): super().__init__('Browser profile denied')


def validate_profile(settings: BrowserSettings, principal: str, seed: ProfileSeed | None):
    """Return the immutable effective settings. Never broaden a cookie's domain or origin."""
    if settings.profile is None:
        if seed is not None: raise ProfileDenied()
        return settings
    if seed is None or seed.principal_id != principal: raise ProfileDenied()
    origins = settings.profile.origins
    hosts = set()
    for value in origins:
        target = urlsplit(value)
        if target.scheme != 'https' or value != DestinationPolicy._origin(value):
            raise ProfileDenied()
        hosts.add(target.hostname)
    if len(seed.model_dump_json().encode()) > 64 * 1024: raise ProfileDenied()
    seen = set()
    for cookie in seed.state.cookies:
        key = (cookie.domain, cookie.path, cookie.name)
        if (cookie.domain not in hosts or cookie.domain.startswith('.') or key in seen
                or (cookie.expires != -1 and cookie.expires <= time.time())): raise ProfileDenied()
        seen.add(key)
    seen.clear()
    for item in seed.state.origins:
        if item.origin not in origins or item.origin in seen: raise ProfileDenied()
        seen.add(item.origin)
        if len({entry.name for entry in item.localStorage}) != len(item.localStorage): raise ProfileDenied()
    return settings.model_copy(update={'allowed_origins': list(origins)})


def parse_seed(settings, principal, raw):
    try:
        seed = ProfileSeed(principal_id=principal, state=ProfileState.model_validate(json.loads(raw)))
        validate_profile(settings, principal, seed)
        return seed
    except (ValueError, TypeError, ProfileDenied): raise ProfileDenied() from None
