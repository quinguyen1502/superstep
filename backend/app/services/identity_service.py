"""Linking a chat account to a studio user, proven by a one-time code ( follow-up, ).

link -> the account is stored unverified; send_code -> the bot DMs a 6-digit code to that account; verify -> the
user types it back. Only verified links map button presses to studio users. Codes are stored as an HMAC, expire
(STUDIO_IDENTITY_CODE_TTL), allow STUDIO_IDENTITY_CODE_ATTEMPTS wrong tries and can be resent every
STUDIO_IDENTITY_CODE_RESEND seconds. Links are per platform and, for Slack, per workspace (team_id); an account
has at most one verified owner per workspace (IDENTITY_TAKEN).
"""
import hashlib, hmac, secrets as pysecrets, time
from ..core import config, crypto
from ..core.errors import AppError
from ..repositories import ApprovalRepository, UserRepository
from .approval_channels import ApprovalChannel
from .channel_service import ChannelService
from .approval_channels.messages import lang_of, text


class IdentityService:
    def __init__(self, repo: ApprovalRepository, users: UserRepository, channels: ChannelService):
        """channels: which connections may DM this user (personal, else org; per workspace for Slack)."""
        self.repo, self.users, self.channels, self.adapters = repo, users, channels, channels.adapters

    def _adapter(self, kind: str) -> ApprovalChannel:
        if kind not in self.adapters or self.adapters[kind].events_only: raise AppError("CHANNEL_KIND_UNSUPPORTED", kind=kind)
        return self.adapters[kind]

    @staticmethod
    def _hash(uid: str, kind: str, team: str, external_id: str, code: str) -> str:
        return hmac.new(crypto.derive_key("identity-code"), f"{uid}:{kind}:{team}:{external_id}:{code}".encode(), hashlib.sha256).hexdigest()

    def _team(self, uid: str, a: ApprovalChannel, body) -> str:
        """The workspace a request is about: body.team_id; may be left out when the user can use exactly one
        workspace of that platform. "" for platforms without workspaces."""
        if not a.per_team: return ""
        team = body.get("team_id") if isinstance(body, dict) else None
        if isinstance(team, str) and team.strip(): return team.strip()
        ws = self.channels.workspaces(uid, a.kind)
        if len(ws) == 1: return ws[0].team_id
        if not ws: raise AppError("CHANNEL_NOT_FOUND")
        raise AppError("CHANNEL_CONFIG_INVALID", field="team_id")

    def get(self, uid: str) -> dict:
        """{"slots": [...]}: one slot per platform, or per usable workspace for Slack (plus links whose workspace is
        no longer connected, available=false)."""
        now = time.time(); mine = {(i.kind, i.team_id): i for i in self.repo.identities(uid)}; slots = []
        def slot(kind, team, name, available):
            i = mine.pop((kind, team), None)
            pending = bool(i and i.code_hash and not i.verified_at and (i.code_expires or 0) > now)
            slots.append({"kind": kind, "team_id": team or None, "team_name": name, "available": available, "external_id": i.external_id if i else None,
                          "verified": bool(i and i.verified_at), "code_pending": pending, "code_expires": i.code_expires if pending else None})
        for kind, a in self.adapters.items():
            if a.link_based or a.events_only: continue  # inbound events have no linked approval identity
            if a.per_team:
                for c in self.channels.workspaces(uid, kind): slot(kind, c.team_id, c.name, True)
            else: slot(kind, "", None, self.channels.dm_channel(uid, kind) is not None)
        for (kind, team) in list(mine): slot(kind, team, None, False)  # stale: workspace not connected (any more)
        return {"slots": slots}

    def link(self, uid: str, body) -> dict:
        """{kind, team_id?, external_id} ("" unlinks). A new or changed account starts unverified."""
        if not isinstance(body, dict): raise AppError("IDENTITY_INVALID", kind="channel")
        a = self._adapter(str(body.get("kind") or "")); team = self._team(uid, a, body)
        v = body.get("external_id"); v = v.strip() if isinstance(v, str) else v
        if v and (not isinstance(v, str) or not a.valid_identity(v)): raise AppError("IDENTITY_INVALID", kind=a.label)
        self.repo.put_identity(uid, a.kind, team, v or None)
        return self.get(uid)

    def send_code(self, uid: str, kind: str, body=None) -> dict:
        a = self._adapter(kind); team = self._team(uid, a, body); i = self.repo.identity(uid, kind, team)
        if i is None: raise AppError("IDENTITY_NOT_LINKED", kind=a.label)
        if i.verified_at: return self.get(uid)
        now = time.time(); wait = int((i.code_sent_at or 0) + config.identity_code_resend() - now + 0.999)
        if wait > 0: raise AppError("RATE_LIMITED", headers={"Retry-After": str(wait)}, retry_after=wait)
        via = self.channels.dm_channel(uid, kind, team)
        if via is None: raise AppError("CHANNEL_NOT_FOUND")
        code = f"{pysecrets.randbelow(10**6):06d}"
        via[0].send_dm(via[1], i.external_id, text(lang_of(self.users.get_by_id(uid)), "code", code=code, minutes=int(config.identity_code_ttl() // 60)))  # 502 CHANNEL_API_FAILED (e.g. the user never started the bot)
        self.repo.set_identity(uid, kind, team, code_hash=self._hash(uid, kind, team, i.external_id, code), code_expires=now + config.identity_code_ttl(),
                               code_sent_at=now, code_attempts=0)
        return self.get(uid)

    def verify(self, uid: str, kind: str, body) -> dict:
        a = self._adapter(kind); team = self._team(uid, a, body); i = self.repo.identity(uid, kind, team)
        code = str((body or {}).get("code") or "").strip() if isinstance(body, dict) else ""
        if i is None: raise AppError("IDENTITY_NOT_LINKED", kind=a.label)
        if i.verified_at: return self.get(uid)
        if not i.code_hash or time.time() > (i.code_expires or 0): raise AppError("IDENTITY_CODE_EXPIRED")
        limit = config.identity_code_attempts()
        if i.code_attempts >= limit: raise AppError("IDENTITY_CODE_ATTEMPTS")
        if not hmac.compare_digest(self._hash(uid, kind, team, i.external_id, code), i.code_hash):
            left = max(0, limit - self.repo.count_attempt(uid, kind, team))
            if left == 0: raise AppError("IDENTITY_CODE_ATTEMPTS")
            raise AppError("IDENTITY_CODE_INVALID", left=left)
        other = self.repo.user_for(kind, i.external_id, team)
        if other is not None and other != uid: raise AppError("IDENTITY_TAKEN", kind=a.label)
        if not self.repo.verify_identity(uid, kind, team, time.time()):  # lost a concurrent verify: the index decides
            raise AppError("IDENTITY_TAKEN", kind=a.label)
        return self.get(uid)
