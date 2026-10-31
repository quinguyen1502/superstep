"""Human-in-the-loop approval through external channels (TASK-0022, DEC-0019)."""
from typing import Optional
from sqlalchemy import text, Boolean, Float, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class ApprovalChannel(Base):
    """A connected channel (Slack app / Telegram bot); secrets are one Fernet-encrypted JSON.
    scope "user": usable by its owner only. scope "org": created by an admin (owner), usable by every user."""
    __tablename__ = "approval_channels"
    __table_args__ = (Index("ix_approval_channels_team", "kind", "team_id"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[str] = mapped_column(Text, index=True)
    kind: Mapped[str] = mapped_column(Text)              # slack | telegram (registry in services/approval_channels)
    scope: Mapped[str] = mapped_column(Text, default="user", server_default="user", index=True)  # user | org
    name: Mapped[Optional[str]] = mapped_column(Text)    # display name (workspace / bot), read from the platform
    team_id: Mapped[Optional[str]] = mapped_column(Text)  # platform account: Slack team id (routes the shared URL) / Telegram bot id
    secrets: Mapped[str] = mapped_column(Text)           # Fernet token of {field: value}; never returned by the API
    hint: Mapped[Optional[str]] = mapped_column(Text)    # masked last 4 chars of the main token
    scopes: Mapped[Optional[str]] = mapped_column(Text)  # Slack: granted OAuth scopes, comma-separated, as last read (TASK-0074); NULL = unknown
    created: Mapped[float] = mapped_column(Float)


class ChannelIdentity(Base):
    """Maps a channel account (Slack user id in one workspace, Telegram user id) to a studio user. Only a *verified* link
    (the user typed the one-time code the bot sent to that account) authorizes button presses; one verified link per
    (kind, team_id, external_id)."""
    __tablename__ = "channel_identities"
    __table_args__ = (Index("ix_channel_identities_external", "kind", "external_id"),
                      Index("uq_channel_identities_verified", "kind", "team_id", "external_id", unique=True,  # one verified owner per account
                            sqlite_where=text("verified_at IS NOT NULL"), postgresql_where=text("verified_at IS NOT NULL")))
    user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, primary_key=True)
    team_id: Mapped[str] = mapped_column(Text, primary_key=True, default="", server_default="")  # Slack workspace; "" = no workspaces (Telegram)
    external_id: Mapped[str] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float)
    verified_at: Mapped[Optional[float]] = mapped_column(Float)
    code_hash: Mapped[Optional[str]] = mapped_column(Text)       # HMAC of the pending one-time code (never the code)
    code_expires: Mapped[Optional[float]] = mapped_column(Float)
    code_sent_at: Mapped[Optional[float]] = mapped_column(Float)  # resend throttle
    code_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # wrong codes for the pending one


class ApprovalRequest(Base):
    """One approval message sent for a waiting run. Tokens are signed with `nonce` + `expires`; single use = CAS on status."""
    __tablename__ = "approval_requests"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(Text, index=True)
    node_id: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(Text, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(Text)
    channel_id: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    target: Mapped[str] = mapped_column(Text)             # Slack channel id / Telegram chat id
    approvers: Mapped[str] = mapped_column(Text)          # JSON list of studio user ids allowed besides the owner
    nonce: Mapped[str] = mapped_column(Text)
    expires: Mapped[float] = mapped_column(Float)
    message_ref: Mapped[Optional[str]] = mapped_column(Text)  # JSON, e.g. {channel, ts} / {chat_id, message_id}
    status: Mapped[str] = mapped_column(Text)             # pending | approved | rejected | expired | superseded | failed
    decided_by: Mapped[Optional[str]] = mapped_column(Text)   # studio user id
    decided_external: Mapped[Optional[str]] = mapped_column(Text)
    decided_at: Mapped[Optional[float]] = mapped_column(Float)
    created: Mapped[float] = mapped_column(Float)


class ApprovalAudit(Base):
    """Append-only log of every approval request, decision and refused attempt."""
    __tablename__ = "approval_audit"
    __table_args__ = (Index("ix_approval_audit_workflow_created", "workflow_id", "created"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[str] = mapped_column(Text, index=True)  # run owner (who may read the entry)
    request_id: Mapped[Optional[str]] = mapped_column(Text)
    run_id: Mapped[Optional[str]] = mapped_column(Text)
    workflow_id: Mapped[Optional[str]] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)  # requested | approved | rejected | denied | superseded | expired | send_failed | not_configured
    code: Mapped[Optional[str]] = mapped_column(Text)  # error code of a refused attempt / failure
    actor_id: Mapped[Optional[str]] = mapped_column(Text)     # studio user id (when mapped)
    external_id: Mapped[Optional[str]] = mapped_column(Text)  # channel user id
    created: Mapped[float] = mapped_column(Float, index=True)
    # AI review (TASK-0186, DEC-0075 decision 7): set on the entry of an AI review and on a human answer after a suggestion
    auto_outcome: Mapped[Optional[str]] = mapped_column(Text)       # approved | rejected | escalated | suggested
    auto_confidence: Mapped[Optional[float]] = mapped_column(Float)
    auto_model: Mapped[Optional[str]] = mapped_column(Text)
    auto_reason: Mapped[Optional[str]] = mapped_column(Text)
    auto_rules: Mapped[Optional[str]] = mapped_column(Text)         # JSON list of the rule numbers that matched
    policy_hash: Mapped[Optional[str]] = mapped_column(Text)
    agreed: Mapped[Optional[bool]] = mapped_column(Boolean)         # a human answer after a suggestion: same as the AI's?


class ApprovalWait(Base):
    """One pause of a run at a Human node, with or without a channel (TASK-0065, DEC-0043). The Approvals inbox reads
    it, and closing it (compare-and-set waiting -> closed) is the gate for "first answer wins"."""
    __tablename__ = "approval_waits"
    __table_args__ = (Index("ix_approval_waits_owner_status", "owner", "status"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(Text, index=True)
    node_id: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(Text)              # run owner
    workflow_id: Mapped[Optional[str]] = mapped_column(Text)
    label: Mapped[Optional[str]] = mapped_column(Text)    # the Human node's label
    prompt: Mapped[Optional[str]] = mapped_column(Text)   # the question, as rendered for this run
    channel: Mapped[Optional[str]] = mapped_column(Text)  # channel kind the node asks on (None = studio only)
    status: Mapped[str] = mapped_column(Text)             # waiting | closed
    outcome: Mapped[Optional[str]] = mapped_column(Text)  # answered | cancelled | expired | error | timeout | superseded | deadline
    created: Mapped[float] = mapped_column(Float)
    closed_at: Mapped[Optional[float]] = mapped_column(Float)
    # deadlines (TASK-0066): read from the run's own workflow snapshot when the step starts waiting
    approval: Mapped[Optional[str]] = mapped_column(Text)    # JSON: the node's data.approval (channel, target), for reminders
    deadline: Mapped[Optional[str]] = mapped_column(Text)    # JSON: engine.deadlines.parse() (seconds)
    due_at: Mapped[Optional[float]] = mapped_column(Float, index=True)
    next_remind_at: Mapped[Optional[float]] = mapped_column(Float, index=True)
    reminders: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    escalated_at: Mapped[Optional[float]] = mapped_column(Float)
    # AI review (TASK-0186): the opinion shown to people (suggest mode, or auto mode that escalated)
    ai_decision: Mapped[Optional[str]] = mapped_column(Text)     # approve | reject | escalate
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float)
    ai_reason: Mapped[Optional[str]] = mapped_column(Text)
    review: Mapped[Optional[str]] = mapped_column(Text)  # AI review of this step: auto | suggest while running, then done (None: no AI review; TASK-0204)


class ApprovalAutoQuota(Base):
    """Automatic answers reserved per workflow per UTC day: the daily cap of AI review, reserved atomically (TASK-0204)."""
    __tablename__ = "approval_auto_quota"
    workflow_id: Mapped[str] = mapped_column(Text, primary_key=True)
    day: Mapped[float] = mapped_column(Float, primary_key=True)
    used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ApprovalWaitApprover(Base):
    """A studio user, besides the run owner, who may answer this waiting step (the node's approvers, resolved by e-mail)."""
    __tablename__ = "approval_wait_approvers"
    wait_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, primary_key=True, index=True)
