"""Browser connection metadata and discovery. Execution requires the later egress/runtime gates."""
from pydantic import ValidationError

from ...core import config
from ...core.errors import AppError
from ...engine.browser_contract import BrowserSettings, tool_definitions


class BrowserTools:
    id = "browser"
    # Browserless token is required for provider=browserless. profile_state is optional encrypted
    # origin-scoped login seed; proxy secrets follow proxy.auth.
    secret_fields = ("browserless_token", "proxy_username", "proxy_password", "profile_state")
    settings_limit = 16384
    settings_schema = BrowserSettings.model_json_schema()

    @staticmethod
    def enabled():
        if not config.browser_enabled():
            raise AppError("BROWSER_DISABLED")

    @staticmethod
    def settings(value):
        try:
            return BrowserSettings.model_validate(value)
        except (ValidationError, ValueError, TypeError):
            raise AppError("MCP_CONFIG_INVALID", field="settings") from None

    def validate(self, uid, settings, secrets):
        self.enabled()
        parsed = self.settings(settings)
        if set(secrets) - set(self.secret_fields):
            raise AppError("MCP_CONFIG_INVALID", field="secrets")
        token = secrets.get("browserless_token")
        if parsed.provider == "browserless":
            if not token or not isinstance(token, str) or len(token) > 512:
                raise AppError("MCP_CONFIG_INVALID", field="secrets.browserless_token")
            if any(ord(c) <= 32 or ord(c) == 127 for c in token):
                raise AppError("MCP_CONFIG_INVALID", field="secrets.browserless_token")
        elif token is not None:
            raise AppError("MCP_CONFIG_INVALID", field="secrets.browserless_token")
        from ...engine.browser_profiles import parse_seed, ProfileDenied
        if parsed.profile:
            try:
                parse_seed(parsed, "user:" + str(uid), secrets.get("profile_state"))
            except ProfileDenied:
                raise AppError("BROWSER_PROFILE_DENIED") from None
        elif "profile_state" in secrets:
            raise AppError("BROWSER_PROFILE_DENIED")
        username, password = secrets.get("proxy_username"), secrets.get("proxy_password")
        if parsed.proxy.auth == "basic":
            if not username or not password:
                raise AppError("MCP_CONFIG_INVALID", field="secrets.proxy_auth")
            if any(ord(c) < 32 or ord(c) == 127 for c in username + password):
                raise AppError("MCP_CONFIG_INVALID", field="secrets.proxy_auth")
        elif username is not None or password is not None:
            raise AppError("MCP_CONFIG_INVALID", field="secrets.proxy_auth")

    def authorize(self, uid, settings, allow_org=True):
        self.enabled()
        self.settings(settings)

    def tools(self, settings):
        parsed = self.settings(settings)
        self.authorize(None, settings)
        return tool_definitions(settings=parsed)

    @staticmethod
    def require_runtime():
        # Never enter the stateless managed-result ledger for a live page. The run
        # context/session port and worker are implemented by .
        raise AppError("BROWSER_RUNTIME_UNAVAILABLE")

    def execute(self, *args, **kwargs):
        self.require_runtime()

    def reconcile(self, *args, **kwargs):
        self.require_runtime()
