"""Settings read from environment variables (names and defaults unchanged from the MVP).

Values that tests or operators may change at runtime are functions; the rest are read once.
"""
import os

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

# --- database ---
STUDIO_DB = os.environ.get("STUDIO_DB", os.path.join(BACKEND_DIR, "studio.db"))
# DATABASE_URL overrides STUDIO_DB (e.g. postgresql+psycopg://user:pw@host/db); default is the SQLite file.
def normalise_db_url(url: str) -> str:
    """Accept the common `postgres://` / `postgresql://` forms and pin them to the psycopg (v3) driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix): return "postgresql+psycopg://" + url[len(prefix):]
    return url

DATABASE_URL = normalise_db_url(os.environ.get("DATABASE_URL") or f"sqlite:///{STUDIO_DB}")

# --- redis (TASK-0009): optional; unset = in-memory run bus (single process) ---
REDIS_URL = os.environ.get("REDIS_URL") or None

# --- auth ---
PLACEHOLDER_SECRET = "dev-secret-change-me"
JWT_SECRET = os.environ.get("JWT_SECRET", PLACEHOLDER_SECRET)
JWT_TTL_SECONDS = int(os.environ.get("JWT_TTL_SECONDS", 60 * 60 * 24))
IS_PROD = os.environ.get("STUDIO_ENV", "dev").lower() in ("prod", "production")
DEMO_EMAIL, DEMO_PASSWORD = "admin@example.com", "admin123"

# --- workflows ---
NAME_MAX = 120


def _int(name: str, default: int) -> int:
    try: return int(os.environ.get(name, default))
    except ValueError: return default

# --- runtime limits (TASK-0004); functions so env changes apply per run ---
def run_timeout() -> float: return float(os.environ.get("STUDIO_RUN_TIMEOUT", 120))
def event_max() -> int: return _int("STUDIO_EVENT_MAX_BYTES", 256 * 1024)
def run_max() -> int: return _int("STUDIO_RUN_MAX_BYTES", 2 * 1024 * 1024)
def input_max() -> int: return _int("STUDIO_INPUT_MAX_BYTES", 256 * 1024)
def workflow_max() -> int: return _int("STUDIO_WORKFLOW_MAX_BYTES", 1024 * 1024)
def recursion_limit() -> int: return _int("STUDIO_RECURSION_LIMIT", 25)
def agent_parallel_tools() -> int:
    """Tool calls of one Agent round that may run at once (REQ-0076, DEC-0069).

    Default 4. The Agent setting `parallel_tool_calls` false forces one call. Set
    STUDIO_AGENT_PARALLEL_TOOLS to 1..8 to change the cap. Invalid values stay at 1. Other integers clamp to 1..8.
    """
    raw = os.environ.get("STUDIO_AGENT_PARALLEL_TOOLS")
    if raw is None or not str(raw).strip(): return 4
    try: n = int(raw)
    except ValueError: return 1
    return min(8, max(1, n))
def allow_private_callbacks() -> bool: return os.environ.get("STUDIO_ALLOW_PRIVATE_CALLBACKS") == "1"
def worker_enabled() -> bool: return os.environ.get("STUDIO_WORKER", "1") != "0"  # run queued jobs in this API process
def worker_concurrency() -> int: return max(1, _int("STUDIO_WORKER_CONCURRENCY", 2))
def auto_approval_enabled() -> bool:  # STUDIO_AUTO_APPROVAL=off: AI review of approvals never answers (REQ-0081)
    return (os.environ.get("STUDIO_AUTO_APPROVAL") or "on").strip().lower() not in ("0", "off", "false", "no")
def wait_ttl() -> float: return max(0.0, float(os.environ.get("STUDIO_WAIT_TTL", 7 * 86400)))  # waiting runs expire (0 = never)
def sync_wait_max() -> float: return max(0.0, float(os.environ.get("STUDIO_SYNC_WAIT_MAX", 30)))  # sync trigger: then 202 + poll URL
def trigger_rate_limit() -> int: return max(0, _int("STUDIO_TRIGGER_RATE_LIMIT", 60))  # runs per token per window (0 = off)
def trigger_rate_window() -> int: return max(1, _int("STUDIO_TRIGGER_RATE_WINDOW", 60))  # seconds
def chat_trigger_rate_limit() -> int: return max(0, _int("STUDIO_CHAT_TRIGGER_RATE_LIMIT", 60))  # runs per sender and chat trigger per STUDIO_TRIGGER_RATE_WINDOW (0 = off)
# the published chat page (TASK-0140, DEC-0067): fixed windows of STUDIO_PUBLIC_CHAT_RATE_WINDOW seconds, 0 = off
def public_chat_rate_visitor() -> int: return max(0, _int("STUDIO_PUBLIC_CHAT_RATE_VISITOR", 10))  # messages per visitor
def public_chat_rate_ip() -> int: return max(0, _int("STUDIO_PUBLIC_CHAT_RATE_IP", 30))  # messages per client IP
def public_chat_rate_read() -> int: return max(0, _int("STUDIO_PUBLIC_CHAT_RATE_READ", 120))  # page, session reads and new chats per client IP
def public_chat_rate_window() -> int: return max(1, _int("STUDIO_PUBLIC_CHAT_RATE_WINDOW", 60))
def chat_attachment_max_mb() -> int:
    """The ceiling on a chat attachment's size in MB (REQ-0077, DEC-0072 decision 3); each chat may only lower it."""
    return max(1, _int("STUDIO_CHAT_ATTACHMENT_MAX_MB", 10))
def chat_attachment_max_files() -> int:
    """The ceiling on files per chat message (DEC-0072 decision 3); each chat may only lower it."""
    return max(1, _int("STUDIO_CHAT_ATTACHMENT_MAX_FILES", 5))
def attachment_storage() -> str:
    """Where new chat attachment bytes go (TASK-0191, REQ-0080, DEC-0074): db (default), fs or s3."""
    return (os.environ.get("STUDIO_ATTACHMENT_STORAGE") or "db").strip().lower()
def data_paths() -> list[str]:
    """Files and folders the studio keeps its own data in (TASK-0203): an `fs` attachment folder must not be or hold them."""
    paths = [home_dir(), os.environ.get("STUDIO_SECRET_KEY_FILE") or os.path.join(home_dir(), "secret.key"),
             os.environ.get("STUDIO_DB", STUDIO_DB)]  # the SQLite file even on Postgres: a later switch back must not lose it
    if os.environ.get("STUDIO_IMPORT_DIR"): paths.append(os.environ["STUDIO_IMPORT_DIR"])
    return [os.path.abspath(os.path.expanduser(p)) for p in paths]
def attachment_s3() -> dict:
    """The `s3` attachment backend's settings (TASK-0193). Empty keys use the default AWS credential chain."""
    e = lambda k: (os.environ.get(f"STUDIO_ATTACHMENT_S3_{k}") or "").strip()  # noqa: E731
    return {"bucket": e("BUCKET"), "prefix": e("PREFIX"), "endpoint": e("ENDPOINT"), "region": e("REGION"),
            "access_key": e("ACCESS_KEY_ID"), "secret_key": e("SECRET_ACCESS_KEY"),
            "path_style": e("PATH_STYLE").lower() in ("1", "true", "yes", "on"),
            "part_mb": max(5, _int("STUDIO_ATTACHMENT_S3_MULTIPART_MB", 8))}  # TASK-0200: larger files go up in parts of this size
def attachment_fs_path() -> str:
    """The folder of the `fs` attachment backend (TASK-0192); on the data volume by default."""
    return (os.environ.get("STUDIO_ATTACHMENT_FS_PATH") or "/data/attachments").strip()
def version_keep() -> int: return max(0, _int("STUDIO_VERSION_KEEP", 0))  # keep last N versions (0 = all)
# --- TASK-0020 ---
def webhook_max_attempts() -> int: return max(1, _int("STUDIO_WEBHOOK_MAX_ATTEMPTS", 5))
def webhook_backoff_base() -> float: return max(0.0, float(os.environ.get("STUDIO_WEBHOOK_BACKOFF_BASE", 2)))  # s; delay = base * 2^(n-1)
def webhook_backoff_max() -> float: return max(0.0, float(os.environ.get("STUDIO_WEBHOOK_BACKOFF_MAX", 300)))
def secret_grace() -> float: return max(0.0, float(os.environ.get("STUDIO_SECRET_GRACE", 24 * 3600)))  # old signing secret stays valid
def job_visibility() -> int: return max(3, _int("STUDIO_JOB_VISIBILITY_TIMEOUT", 30))  # lease of a taken job
def recover_on_start() -> bool: return os.environ.get("STUDIO_RECOVER_ON_START", "1") != "0"  # in-memory queue: requeue unfinished runs at start-up
def recover_max_attempts() -> int: return max(1, _int("STUDIO_RECOVER_MAX_ATTEMPTS", 3))  # restarts that may cut one run off before recovery gives up (resumes do not count)
def job_reap_every() -> float: return max(0.2, float(os.environ.get("STUDIO_JOB_REAP_EVERY", 15)))
def static_dir() -> str: return os.environ.get("STUDIO_STATIC_DIR", "")  # built frontend served by the API (all-in-one image); empty = off
def public_url() -> str: return (os.environ.get("STUDIO_PUBLIC_URL") or "").rstrip("/")  # links in e-mails
# --- TASK-0045: sign-in hardening ---
def login_max_failures() -> int: return max(1, _int("STUDIO_LOGIN_MAX_FAILURES", 5))  # failed sign-ins per e-mail before a lockout
def login_window() -> int: return max(1, _int("STUDIO_LOGIN_WINDOW", 15 * 60))  # s in which failures are counted
def login_lock() -> int: return max(1, _int("STUDIO_LOGIN_LOCK", 15 * 60))  # s an e-mail stays locked
def password_reset_ttl() -> int: return max(60, _int("STUDIO_PASSWORD_RESET_TTL", 3600))  # s a reset link works
def cookie_secure() -> bool:  # the session cookie needs HTTPS; production defaults to on, STUDIO_COOKIE_SECURE=0 for plain-HTTP setups
    return os.environ.get("STUDIO_COOKIE_SECURE", "1" if IS_PROD else "0").lower() in ("1", "true", "yes", "on")
def home_dir() -> str:
    """Default directory for the generated secret key and repo imports (Docker sets both paths to /data instead).
    `~/.superstep`, or the v0.1.0 `~/.langgraph-studio` while only that one exists, so stored credentials still decrypt
    after the rename (TASK-0058)."""
    new, old = os.path.expanduser("~/.superstep"), os.path.expanduser("~/.langgraph-studio")
    return old if not os.path.exists(new) and os.path.isdir(old) else new


def demo_mode() -> bool:
    """STUDIO_DEMO_MODE=true: the public demo (services/demo_service.py). Code nodes, HTTP and Send email nodes are off,
    models use the offline mock, and each visitor gets a temporary read-only account of their own. Never turn it on for real work."""
    return (os.environ.get("STUDIO_DEMO_MODE") or "").strip().lower() in ("1", "true", "yes", "on")
def demo_visitor_ttl() -> float: return max(60.0, float(_int("STUDIO_DEMO_VISITOR_TTL", 24 * 3600)))  # demo: a visitor's runs and chats are removed after (s)
def demo_run_rate_limit() -> int: return max(0, _int("STUDIO_DEMO_RUN_RATE_LIMIT", 20))  # runs per client IP per minute in demo mode (0 = off)
def demo_user() -> bool: return not IS_PROD  # the seeded admin@example.com / admin123 account exists only outside production
def smtp() -> dict | None:
    """The studio's own SMTP server (notification, approval and password reset e-mail; core/smtp.py settings); None
    (no-op) when SMTP_HOST is unset. The admin chose it, so private addresses are allowed and STARTTLS is used when offered."""
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host: return None
    security = "ssl" if os.environ.get("SMTP_SSL") == "1" else "starttls" if os.environ.get("SMTP_STARTTLS", "1") != "0" else "none"
    return {"host": host, "port": _int("SMTP_PORT", 587), "username": os.environ.get("SMTP_USER") or None,
            "password": os.environ.get("SMTP_PASSWORD") or None, "sender": os.environ.get("SMTP_FROM") or "studio@localhost",
            "security": security, "allow_private": True, "tls_optional": True}
# --- TASK-0051: Send email nodes ---
def email_node_allow_private() -> bool: return os.environ.get("STUDIO_SMTP_ALLOW_PRIVATE") == "1"  # SMTP credentials may use private/loopback hosts
def email_node_hourly_limit() -> int: return max(1, _int("STUDIO_EMAIL_NODE_HOURLY_LIMIT", 100))  # e-mails Send email nodes may send per resource owner per hour
def notify_webhook() -> tuple[str, str | None] | None:
    url = os.environ.get("STUDIO_NOTIFY_WEBHOOK_URL", "").strip()
    return (url, os.environ.get("STUDIO_NOTIFY_WEBHOOK_SECRET") or None) if url else None
def otel_metrics() -> bool: return os.environ.get("STUDIO_OTEL_METRICS", "").lower() in ("1", "true", "yes", "on")
# --- TASK-0022: approval through external channels ---
def approval_ttl() -> float: return max(60.0, float(os.environ.get("STUDIO_APPROVAL_TTL", 24 * 3600)))  # approval buttons expire (s)
def slack_api_url() -> str: return (os.environ.get("SLACK_API_URL") or "https://slack.com/api").rstrip("/")
# Add to Slack / OAuth app distribution (TASK-0014): all three from the Slack app's "Basic Information" page
def slack_client_id() -> str: return (os.environ.get("SLACK_CLIENT_ID") or "").strip()
def slack_client_secret() -> str: return (os.environ.get("SLACK_CLIENT_SECRET") or "").strip()
def slack_signing_secret() -> str: return (os.environ.get("SLACK_SIGNING_SECRET") or "").strip()
def slack_oauth_url() -> str: return (os.environ.get("SLACK_OAUTH_URL") or "https://slack.com/oauth/v2/authorize").rstrip("/")
SLACK_BOT_SCOPES = "chat:write,chat:write.public,im:write,app_mentions:read,im:history"  # same as the manual setup (handbook); the last two: chat triggers
def telegram_api_url() -> str: return (os.environ.get("TELEGRAM_API_URL") or "https://api.telegram.org").rstrip("/")
def whatsapp_api_url() -> str: return (os.environ.get("WHATSAPP_API_URL") or "https://graph.facebook.com/v21.0").rstrip("/")  # TASK-0047
def llm_mode() -> str: return "openai" if os.environ.get("OPENAI_API_KEY") else "mock"
# --- TASK-0022 follow-up: identity verification codes sent by the bot ---
def identity_code_ttl() -> float: return max(60.0, float(os.environ.get("STUDIO_IDENTITY_CODE_TTL", 600)))  # a code is valid (s)
def identity_code_attempts() -> int: return max(1, _int("STUDIO_IDENTITY_CODE_ATTEMPTS", 5))  # wrong codes before a new one is needed
def identity_code_resend() -> int: return max(0, _int("STUDIO_IDENTITY_CODE_RESEND", 30))     # min seconds between two codes
# --- TASK-0022 follow-up: org-wide approval channels ---
def admin_emails() -> set[str]: return {e.strip().lower() for e in (os.environ.get("STUDIO_ADMIN_EMAILS") or "").split(",") if e.strip()}
def default_role() -> str:  # role of newly registered accounts (TASK-0014): editor | viewer (admin is never a default)
    r = (os.environ.get("STUDIO_DEFAULT_ROLE") or "editor").strip().lower()
    return r if r in ("editor", "viewer") else "editor"
# --- TASK-0022 follow-up: rate limits of the public approval callbacks (fixed window, shared via Redis) ---
def callback_rate_limit_ip() -> int: return max(0, _int("STUDIO_CALLBACK_RATE_LIMIT_IP", 60))        # per client IP and window (0 = off)
def callback_rate_limit_channel() -> int: return max(0, _int("STUDIO_CALLBACK_RATE_LIMIT_CHANNEL", 300))  # per connection / Slack team
def callback_rate_window() -> int: return max(1, _int("STUDIO_CALLBACK_RATE_WINDOW", 60))
# --- TASK-0013: MCP servers ---
def mcp_stdio_enabled() -> bool: return os.environ.get("STUDIO_MCP_STDIO") == "1"  # stdio servers run processes on the API host: off by default
def mcp_allow_private() -> bool: return os.environ.get("STUDIO_MCP_ALLOW_PRIVATE") == "1"  # HTTP servers on private/loopback addresses
def mcp_timeout() -> float: return max(1.0, float(os.environ.get("STUDIO_MCP_TIMEOUT", 30)))  # per MCP session (s)
# --- TASK-0039: HTTP Tool nodes, CORS ---
def http_tool_allow_private() -> bool: return os.environ.get("STUDIO_HTTP_TOOL_ALLOW_PRIVATE") == "1"  # HTTP Tool nodes may call private/loopback addresses
def http_tool_timeout() -> float: return max(1.0, float(os.environ.get("STUDIO_HTTP_TOOL_TIMEOUT", 30)))  # per request (s)
def cors_origins() -> list[str]:
    """STUDIO_CORS_ORIGINS (comma-separated); unset: "*" in development, none in production (the UI is same-origin)."""
    raw = os.environ.get("STUDIO_CORS_ORIGINS")
    if raw is None: return [] if IS_PROD else ["*"]
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
# --- TASK-0015: repo import is experimental and off until STUDIO_ENABLE_IMPORT=1 ---
def import_enabled() -> bool: return os.environ.get("STUDIO_ENABLE_IMPORT") == "1"
def import_runtime() -> str:
    """``docker`` when import is enabled, unless STUDIO_IMPORT_RUNTIME=subprocess."""
    choice = (os.environ.get("STUDIO_IMPORT_RUNTIME") or "").strip().lower()
    if choice in ("docker", "subprocess"): return choice
    return "docker" if import_enabled() else "subprocess"
def import_max_bytes() -> int: return max(1, _int("STUDIO_IMPORT_MAX_BYTES", 200 * 1024 * 1024))
def import_max_age_s() -> float: return max(0, _int("STUDIO_IMPORT_MAX_AGE_HOURS", 72)) * 3600
def import_memory() -> str: return os.environ.get("STUDIO_IMPORT_MEMORY", "1g") or "1g"
def import_cpus() -> str: return os.environ.get("STUDIO_IMPORT_CPUS", "1") or "1"
def import_pids() -> int: return max(32, _int("STUDIO_IMPORT_PIDS", 256))
def import_image() -> str: return os.environ.get("STUDIO_IMPORT_IMAGE", "python:3.12-slim") or "python:3.12-slim"
def import_network() -> str:
    choice = (os.environ.get("STUDIO_IMPORT_NETWORK") or "bridge").strip().lower()
    return choice if choice in ("bridge", "none") else "bridge"
def import_host_dir() -> str | None:
    value = (os.environ.get("STUDIO_IMPORT_HOST_DIR") or "").strip()
    return value or None
# --- TASK-0053: Tool node Code mode (REQ-0039, DEC-0041); off until STUDIO_ENABLE_CODE_NODES=1 ---
CODE_RUNTIMES = ("docker", "subprocess", "remote")  # subprocess (TASK-0056) is NOT isolation; remote = the sandbox service
def code_runtime() -> str:
    """``off`` unless enabled; then STUDIO_CODE_RUNTIME (``docker`` by default). Never falls back to another runtime."""
    if os.environ.get("STUDIO_ENABLE_CODE_NODES") != "1" or demo_mode(): return "off"
    choice = (os.environ.get("STUDIO_CODE_RUNTIME") or "docker").strip().lower()
    return choice if choice in CODE_RUNTIMES else "off"
def code_languages() -> list[str]:
    """STUDIO_CODE_LANGUAGES (TASK-0079): the Code-mode languages offered, comma-separated; ``python,typescript`` by
    default since TASK-0080 (TypeScript reports itself unavailable until its image or the deno binary is there)."""
    raw = os.environ.get("STUDIO_CODE_LANGUAGES") or "python,typescript"
    return [x.strip().lower() for x in raw.split(",") if x.strip()]
def sandbox_url() -> str:
    """STUDIO_SANDBOX_URL: the sandbox service for STUDIO_CODE_RUNTIME=remote; a bare host:port gets http://."""
    url = (os.environ.get("STUDIO_SANDBOX_URL") or "").strip().rstrip("/")
    return url if not url or "://" in url else f"http://{url}"
def sandbox_token() -> str: return os.environ.get("STUDIO_SANDBOX_TOKEN") or ""  # shared by the studio and the sandbox service
def code_no_network() -> bool: return os.environ.get("STUDIO_CODE_NO_NETWORK") == "1"  # Python Code: refuse sockets and processes (audit hook)
def code_run_as() -> int | None:
    """STUDIO_CODE_RUN_AS: first uid for Code processes when the server runs as root (the sandbox service); unset = no change."""
    raw = os.environ.get("STUDIO_CODE_RUN_AS", "").strip()
    return int(raw) if raw.isdigit() else None
def code_image() -> str: return os.environ.get("STUDIO_CODE_IMAGE", "studio-code:1") or "studio-code:1"
def code_memory() -> str: return os.environ.get("STUDIO_CODE_MEMORY", "256m") or "256m"
def code_cpus() -> str: return os.environ.get("STUDIO_CODE_CPUS", "0.5") or "0.5"
def code_pids() -> int: return max(16, _int("STUDIO_CODE_PIDS", 64))
def code_max_seconds() -> int: return max(1, _int("STUDIO_CODE_MAX_SECONDS", 30))  # per call, also caps the node timeout
def code_concurrency() -> int: return max(1, _int("STUDIO_CODE_CONCURRENCY", 4))  # containers at once per process
def test_cases_max() -> int: return max(1, _int("STUDIO_TEST_CASES_MAX", 50))  # test cases per workflow (TASK-0067)
def test_parallel() -> int: return max(1, _int("STUDIO_TEST_PARALLEL", 4))     # test runs of one suite at a time (TASK-0067)
def code_test_per_minute() -> int: return max(1, _int("STUDIO_CODE_TEST_PER_MINUTE", 20))  # Test with sample state, per user
# --- TASK-0080 (DEC-0049): TypeScript on Deno ---
CODE_TS_DEFAULT_PACKAGES = ["npm:zod@3", "npm:date-fns@4"]  # exactly what docker/studio-code-ts caches (deps.ts)
def code_ts_image() -> str: return os.environ.get("STUDIO_CODE_TS_IMAGE", "studio-code-ts:1") or "studio-code-ts:1"
def code_ts_packages() -> list[str]:
    """STUDIO_CODE_TS_PACKAGES (comma-separated `npm:`/`jsr:` specifiers pinned
    to a major version, `name@major`, e.g. `npm:zod@3`) when set; the default image's
    packages for that image; else none. Only these may be imported, and only if they are in Deno's cache."""
    raw = os.environ.get("STUDIO_CODE_TS_PACKAGES")
    if raw is not None: return [x.strip() for x in raw.split(",") if x.strip()]
    return list(CODE_TS_DEFAULT_PACKAGES) if code_ts_image() == "studio-code-ts:1" else []
def deno_exe() -> str | None:
    """STUDIO_DENO, else `deno` on PATH: the binary of the host subprocess runtime for TypeScript."""
    import shutil
    return os.environ.get("STUDIO_DENO") or shutil.which("deno")
def code_ts_deno_dir() -> str:
    """STUDIO_CODE_TS_DENO_DIR: a Deno cache with the allowlisted packages for the host runtime (``deno cache``).
    Empty = a fresh, empty cache per call (no packages)."""
    return os.environ.get("STUDIO_CODE_TS_DENO_DIR", "")
CODE_DEFAULT_PACKAGES = ["pydantic", "python-dateutil"]  # what docker/studio-code adds to the standard library
def code_packages() -> list[str]:
    """STUDIO_CODE_PACKAGES (comma-separated) when set; the default image's packages for that image; else unknown ([])."""
    raw = os.environ.get("STUDIO_CODE_PACKAGES")
    if raw is not None: return [p.strip() for p in raw.split(",") if p.strip()]
    return list(CODE_DEFAULT_PACKAGES) if code_image() == "studio-code:1" else []
