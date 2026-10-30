"""FastAPI dependency wiring: one Database per process, services built per request (cheap)."""
from functools import lru_cache
from urllib.parse import urlparse
from fastapi import Depends, Request, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ..core import config, security
from ..core.errors import AppError
from ..services.notification_hub import NotificationHub, make_notification_hub
from ..models.database import Database
from ..repositories import AgentThreadRepository, ChatAttachmentRepository, ChatSessionRepository, CliDeviceRepository, CredentialRepository, PersonalAccessTokenRepository, RunRepository, UserRepository, WorkflowRepository, WorkflowTokenRepository, WorkflowVersionRepository, NotificationRepository, WebhookDeliveryRepository, NodeResultRepository, ApprovalRepository, KnowledgeRepository, McpServerRepository, WorkflowShareRepository, TeamRepository, AuditRepository, SettingsRepository, UserDataRepository, TemplateRepository, AuthSecurityRepository, ScheduleRepository, ChatTriggerRepository, ChatMessageRepository, WorkflowTestRepository, CredentialRepository as _Creds
from ..services.audit_service import AuditService
from ..services.code_service import CodeService
from ..services.inbox_service import InboxService
from ..services.policy_service import PolicyService
from ..services.team_service import TeamService
from ..services.ownership_service import OwnershipService
from ..core import permissions as P
from ..services.access import AccessService
from ..services.auto_approval_service import AutoApprovalService
from ..services.auto_review_service import AutoReviewService
from ..services.share_service import ShareService
from ..services.user_service import UserService
from ..services.template_service import TemplateService
from ..services.slack_oauth import SlackOAuthService
from ..services.mcp_service import McpService
from ..services.knowledge_service import KnowledgeService
from ..services.approval_service import ApprovalService
from ..services.identity_service import IdentityService
from ..services.channel_service import ChannelService
from ..services.approval_channels import ADAPTERS
from ..services.auth_service import AuthService
from ..services.pat_service import PatService
from ..services.credential_service import CredentialService
from ..services.import_service import ImportService
from ..services.run_bus import RunBus, make_run_bus
from ..services.job_queue import JobQueue, make_job_queue
from ..services.run_service import RunService
from ..services.run_worker import RunWorker
from ..services.delivery_service import DeliveryService
from ..services.notification_service import NotificationService
from ..services.demo_service import DemoService, start_visit
from ..services.rate_limit import Counter, RateLimiter, make_counter, make_rate_limiter
from ..services.trigger_service import TriggerService
from ..services.workflow_mcp_service import WorkflowMcpService
from ..services.langsmith import LangSmithService
from ..services.agent_server_service import AgentServerService
from ..services.schedule_service import ScheduleService
from ..services.chat_trigger_service import ChatTriggerService
from ..services.chat_run_service import ChatRunService
from ..services.chat_session_service import ChatSessionService
from ..services.public_chat_service import PublicChatService
from ..services.chat_attachment_service import ChatAttachmentService
from ..services.telemetry import Telemetry
from ..services.workflow_service import WorkflowService
from ..services.workflow_test_service import WorkflowTestService


@lru_cache
def get_db() -> Database:
    return Database()


@lru_cache
def get_run_bus() -> RunBus:
    return make_run_bus(config.REDIS_URL)  # Redis when REDIS_URL is set, else in-memory


@lru_cache
def get_job_queue() -> JobQueue:
    return make_job_queue(config.REDIS_URL)  # Redis list when REDIS_URL is set, else in-process


@lru_cache
def run_worker() -> RunWorker:
    return RunWorker(get_job_queue(), run_service, delivery_service, schedule_service, approval_service, chat_run_service, langsmith_service)


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return make_rate_limiter(config.REDIS_URL)  # shared via Redis, else per process


@lru_cache
def get_counter() -> Counter:
    return make_counter(config.REDIS_URL)  # blocking twin of the rate limiter for quotas inside runs (TASK-0051)


def delivery_service() -> DeliveryService:
    db = get_db(); return DeliveryService(WebhookDeliveryRepository(db), WorkflowRepository(db), get_job_queue(), trigger_service().signing_secrets,
                                          access=access_service())


@lru_cache
def get_notification_hub() -> NotificationHub:
    return make_notification_hub(config.REDIS_URL)  # Redis pub/sub when REDIS_URL is set, else in-process (TASK-0021)


def notification_service() -> NotificationService:
    db = get_db(); return NotificationService(NotificationRepository(db), UserRepository(db), WorkflowRepository(db), hub=get_notification_hub())


def schedule_service() -> ScheduleService:
    db = get_db(); return ScheduleService(ScheduleRepository(db), WorkflowRepository(db), RunRepository(db), get_job_queue(), access=access_service())


def chat_trigger_service() -> ChatTriggerService:
    db = get_db(); return ChatTriggerService(ChatTriggerRepository(db), WorkflowRepository(db), channel_service(), access=access_service())


def chat_run_service() -> ChatRunService:
    db = get_db(); return ChatRunService(ChatMessageRepository(db), ChatTriggerRepository(db), channel_service(), UserRepository(db), WorkflowRepository(db),
                                         RunRepository(db), get_job_queue(), access=access_service(), limiter=get_rate_limiter(), web=chat_session_service())


def chat_session_service() -> ChatSessionService:
    db = get_db(); return ChatSessionService(ChatSessionRepository(db), ChatTriggerRepository(db), ChatMessageRepository(db), WorkflowRepository(db),
                                             RunRepository(db), access=access_service(), jobs=get_job_queue(), attachments=ChatAttachmentRepository(db))


def public_chat_service() -> PublicChatService:
    return PublicChatService(chat_session_service(), limiter=get_rate_limiter(), counter=get_counter())


def chat_attachment_service() -> ChatAttachmentService:
    pub = public_chat_service(); return ChatAttachmentService(pub.chat.attachments, pub.chat, pub)


def trigger_service() -> TriggerService:
    db = get_db(); return TriggerService(WorkflowRepository(db), RunRepository(db), WorkflowTokenRepository(db), get_job_queue(), get_rate_limiter(),
                                         access=access_service())


def workflow_mcp_service() -> WorkflowMcpService:
    return WorkflowMcpService(trigger_service(), WorkflowRepository(get_db()))


def agent_server_service() -> AgentServerService:
    db = get_db(); return AgentServerService(WorkflowRepository(db), RunRepository(db), AgentThreadRepository(db), trigger_service(),
                                             AuthService(UserRepository(db)).current, access=access_service(), runner=run_service)


@lru_cache
def get_telemetry() -> Telemetry:
    return Telemetry()  # exporters from OTEL_* / LANGSMITH_* env; no-op when none


def workflow_service() -> WorkflowService:
    db = get_db(); return WorkflowService(WorkflowRepository(db), RunRepository(db), WorkflowVersionRepository(db),
                                          access=access_service(), shares=WorkflowShareRepository(db), users=UserRepository(db),
                                          teams=TeamRepository(db), audit=audit_service(), tests=WorkflowTestRepository(db),
                                          chat_triggers=ChatTriggerRepository(db), chat_sessions=ChatSessionRepository(db),
                                          jobs=get_job_queue())

def template_service() -> TemplateService:
    return TemplateService(TemplateRepository(get_db()), workflow_service(), access_service(), tests=workflow_test_service)

def code_service() -> CodeService:
    return CodeService(access_service(), get_rate_limiter(), audit_service())

def access_service() -> AccessService:
    db = get_db(); return AccessService(UserRepository(db), WorkflowRepository(db), WorkflowShareRepository(db), TeamRepository(db))

def audit_service() -> AuditService:
    db = get_db(); return AuditService(AuditRepository(db), UserRepository(db), access_service())

def policy_service() -> PolicyService:
    return PolicyService(SettingsRepository(get_db()), access_service(), audit_service())

def auto_approval_service() -> AutoApprovalService:
    db = get_db(); return AutoApprovalService(SettingsRepository(db), access_service(), audit_service(), reviews=auto_review_service)

def auto_review_service() -> AutoReviewService:
    db = get_db(); creds = credential_service()
    return AutoReviewService(ApprovalRepository(db), AutoApprovalService(SettingsRepository(db)), creds.resolve)

def team_service() -> TeamService:
    db = get_db(); return TeamService(TeamRepository(db), UserRepository(db), access_service(), audit_service())

def ownership_service() -> OwnershipService:
    db = get_db()
    return OwnershipService(WorkflowRepository(db), UserRepository(db), access_service(), WorkflowShareRepository(db), _Creds(db),
                            KnowledgeRepository(db), McpServerRepository(db), audit_service(), workflow_service())

def user_service() -> UserService:
    db = get_db()
    return UserService(UserRepository(db), access_service(), audit_service(), UserDataRepository(db), ownership_service(), WorkflowRepository(db))

def share_service() -> ShareService:
    db = get_db(); return ShareService(WorkflowShareRepository(db), UserRepository(db), access_service(), TeamRepository(db), audit_service())

def pat_service() -> PatService:
    db = get_db(); return PatService(PersonalAccessTokenRepository(db), CliDeviceRepository(db), UserRepository(db))

def _auth() -> AuthService:
    db = get_db(); return AuthService(UserRepository(db), pats=PersonalAccessTokenRepository(db))

def auth_service() -> AuthService:
    db = get_db(); return AuthService(UserRepository(db), workflow_service(), AuthSecurityRepository(db), audit=audit_service(),
                                      visit=lambda: start_visit(db, jobs=get_job_queue()), pats=PersonalAccessTokenRepository(db))

def demo_service() -> DemoService:
    return DemoService(get_rate_limiter())

def run_service() -> RunService:
    db = get_db(); return RunService(WorkflowRepository(db), RunRepository(db), credential_service(), get_run_bus(), get_telemetry(), WorkflowVersionRepository(db), notification_service(), NodeResultRepository(db), approval_service(), delivery_service,
                      knowledge=knowledge_service(), mcp=mcp_service(), access=access_service(),
                      policy=policy_service(), quota=get_counter(), audit=audit_service(), tests=workflow_test_service, chat=chat_run_service,
                      jobs=get_job_queue)

def langsmith_service() -> LangSmithService:
    db = get_db(); return LangSmithService(SettingsRepository(db), access_service(), WorkflowTestRepository(db), WorkflowRepository(db),
                                           RunRepository(db), audit=audit_service(), sessions=ChatSessionRepository(db))

def workflow_test_service() -> WorkflowTestService:
    db = get_db(); return WorkflowTestService(WorkflowTestRepository(db), WorkflowRepository(db), RunRepository(db), WorkflowVersionRepository(db),
                                              get_job_queue(), run_service, access=access_service(), langsmith=langsmith_service)

def channel_service() -> ChannelService:
    db = get_db(); return ChannelService(ApprovalRepository(db), UserRepository(db), ADAPTERS, policy_service().org_allowed, triggers=ChatTriggerRepository(db))

def approval_service() -> ApprovalService:
    db = get_db(); return ApprovalService(ApprovalRepository(db), UserRepository(db), WorkflowRepository(db), RunRepository(db), channel_service(), get_job_queue().enqueue,
                                         limiter=get_rate_limiter(), notifier=notification_service(), chat=chat_run_service,
                                         reviewer=auto_review_service())

def inbox_service() -> InboxService:
    return InboxService(approval_service(), run_service(), access_service())

def slack_oauth_service() -> SlackOAuthService:
    return SlackOAuthService(channel_service(), access_service())

def credential_service() -> CredentialService:
    return CredentialService(CredentialRepository(get_db()))

def knowledge_service() -> KnowledgeService:
    return KnowledgeService(KnowledgeRepository(get_db()), credential_service())

def mcp_service() -> McpService:
    db = get_db(); users = UserRepository(db)
    return McpService(McpServerRepository(db), lambda uid: bool((u := users.get_by_id(uid)) and u.active and P.can(u.role, P.ORG_MANAGE)),
                      policy_service().org_allowed)

def import_service() -> ImportService:
    return ImportService(workflow_service())


bearer = HTTPBearer(auto_error=False)

UNSAFE = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def current_user(request: Request, cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    """The signed-in, active user with role and permissions (database-checked per request, TASK-0014).
    A Bearer token wins; otherwise the session cookie (TASK-0045), whose writes must carry X-Requested-With (CSRF)."""
    token = cred.credentials if cred else None
    if token is None and (token := request.cookies.get(security.SESSION_COOKIE)):
        if request.method in UNSAFE and request.headers.get(security.CSRF_HEADER) != security.CSRF_VALUE: raise AppError("AUTH_CSRF")
    return _auth().current(token)


def _same_origin(origin: str | None, host: str | None) -> bool:
    """The page's host is the server's host (ports ignored: nginx forwards `$host` without one), or an allowed CORS origin."""
    return not origin or urlparse(origin).hostname == (host or "").rsplit(":", 1)[0].strip("[]") or origin in config.cors_origins()


def ws_user(ws: WebSocket) -> dict:
    """WebSocket variant of current_user: ?token= (API clients), else the session cookie from a same-origin page."""
    token = ws.query_params.get("token")
    if not token and (token := ws.cookies.get(security.SESSION_COOKIE)):
        if not _same_origin(ws.headers.get("origin"), ws.headers.get("host")): raise AppError("AUTH_CSRF")
    return _auth().current(token)


def need(permission: str):
    """Route dependency: the current user if their role grants `permission`, else PERMISSION_DENIED."""
    def dep(user: dict = Depends(current_user)) -> dict:
        if permission not in user["permissions"]: raise AppError("PERMISSION_DENIED", permission=permission)
        return user
    return dep


async def limit_body(request: Request):
    n = int(request.headers.get("content-length") or 0)
    if n > config.workflow_max(): raise AppError("WORKFLOW_TOO_LARGE", max_kb=config.workflow_max() // 1024)


def identity_service() -> IdentityService:
    ch = channel_service(); return IdentityService(ch.repo, ch.users, ch)
