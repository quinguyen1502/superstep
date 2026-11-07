"""Profiles use existing encrypted personal connection storage; no separate capture/login UI."""
import hashlib
import json

from ..core.errors import AppError
from ..engine.browser_contract import BrowserSettings
from ..engine.browser_profiles import ProfileDenied, parse_seed, validate_profile
from .mcp_service import McpService


def browser_configuration(connection):
    # Ciphertext participates: a credential/profile update invalidates even unchanged metadata.
    value = [connection.id, connection.owner, connection.scope, connection.adapter, connection.settings, connection.secrets]
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


class BrowserProfileService:
    @staticmethod
    def prepare(connection, context):
        if (connection.adapter != 'browser' or context.connection_id != connection.id
                or context.configuration != browser_configuration(connection)):
            raise AppError('BROWSER_PROFILE_DENIED')
        settings = BrowserSettings.model_validate(json.loads(connection.settings or '{}'))
        secrets = McpService._stored(connection)
        if settings.profile is None: return settings, None
        if connection.scope != 'user' or context.principal_id != 'user:' + connection.owner:
            raise AppError('BROWSER_PROFILE_DENIED')
        try:
            seed = parse_seed(settings, context.principal_id, secrets.get('profile_state'))
            return validate_profile(settings, context.principal_id, seed), seed
        except ProfileDenied: raise AppError('BROWSER_PROFILE_DENIED') from None
