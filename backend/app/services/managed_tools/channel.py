"""One authorisation boundary for every managed action backed by an existing channel."""
from ...core.errors import AppError


class ChannelTools:
    secret_fields = ()

    def __init__(self, channels): self.channels = channels

    def authorize(self, uid, settings, allow_org=True):
        cid = settings.get("channel_id")
        channel = self.channels.repo.channel(cid) if self.channels and isinstance(cid, str) and 1 <= len(cid) <= 100 else None
        if not self.channels or not self.channels.usable(uid, channel) or channel.kind != self.id or (channel.scope == "org" and (not allow_org or not self.channels.org_allowed(uid))):
            raise AppError("CHANNEL_NOT_FOUND")
        return channel

    def validate(self, uid, settings, secrets):
        if set(settings) != set(self.settings_schema["properties"]) or secrets: raise AppError("MCP_CONFIG_INVALID", field="settings")
        self.validate_target(settings)
        self.authorize(uid, settings)

    def validate_target(self, settings): pass

    def reconcile(self, uid, settings, secrets, tool, key, allow_org=True):
        self.authorize(uid, settings, allow_org)
        return None  # No universal read-only message lookup; never resend an uncertain send.
