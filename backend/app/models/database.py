"""Engine/session factory and schema migration (Alembic) bootstrap."""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event, literal, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from ..core import config
from ..core.dataset_types import TEXT_FOLD_FUNCTION, fold_text

try: import fcntl
except ImportError: fcntl = None  # Windows: no file lock (single dev process)

MIGRATION_LOCK_KEY = 726_150_019  # arbitrary app-wide constant for pg_advisory_xact_lock
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")


def make_engine(url: str | None = None) -> Engine:
    url = config.normalise_db_url(url or config.DATABASE_URL)
    sqlite = url.startswith("sqlite")
    eng = create_engine(url, future=True, connect_args={"check_same_thread": False, "timeout": 15} if sqlite else {"connect_timeout": 10},
                        pool_pre_ping=not sqlite)
    if sqlite:
        @event.listens_for(eng, "connect")
        def _pragmas(dbapi_conn, _):  # same behaviour as the MVP: WAL + 15 s busy timeout
            cur = dbapi_conn.cursor(); cur.execute("PRAGMA journal_mode=WAL"); cur.close()
            dbapi_conn.create_function(TEXT_FOLD_FUNCTION, 1, fold_text, deterministic=True)
    return eng


class Database:
    """Owns the engine and hands out sessions; one instance per app (see api.deps)."""
    def __init__(self, url: str | None = None):
        self.url = config.normalise_db_url(url or config.DATABASE_URL)
        self.engine = make_engine(self.url)
        self._factory = sessionmaker(self.engine, expire_on_commit=False)

    def session(self) -> Session:
        return self._factory()

    def ping(self) -> bool:
        """One round trip to the database (readiness probe)."""
        with self.engine.connect() as conn:
            return conn.execute(select(literal(1))).scalar() == 1

    def pool_status(self) -> dict:
        """Connections of this process's pool: checked out (in use), idle in the pool, and overflow beyond pool_size.
        Empty for pools that do not count (e.g. a static pool)."""
        pool = self.engine.pool
        try: return {"in_use": pool.checkedout(), "idle": pool.checkedin(), "overflow": max(0, pool.overflow())}
        except AttributeError: return {}

    def migrate(self) -> None:
        """Upgrade to the latest Alembic revision (idempotent; adopts pre-Alembic SQLite files).
        Serialised across processes: a Postgres advisory lock held for the migration transaction,
        or an exclusive file lock next to a SQLite database file, so API replicas + workers can start together."""
        from alembic import command
        from alembic.config import Config
        cfg = Config()
        cfg.set_main_option("script_location", os.path.normpath(MIGRATIONS_DIR))
        cfg.set_main_option("sqlalchemy.url", self.url.replace("%", "%%"))
        with self._file_lock():
            with self.engine.begin() as conn:
                if conn.dialect.name == "postgresql":
                    conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": MIGRATION_LOCK_KEY})  # released at commit
                cfg.attributes["connection"] = conn
                command.upgrade(cfg, "head")

    @contextmanager
    def _file_lock(self):
        path = sqlite_file(self.url)
        if path is None or fcntl is None:  # Postgres (advisory lock instead), in-memory SQLite, or no fcntl (Windows)
            yield; return
        with open(path + ".migrate.lock", "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(f, fcntl.LOCK_UN)


def sqlite_file(url: str) -> str | None:
    """Filesystem path of a file-based SQLite URL, else None."""
    if not url.startswith("sqlite"): return None
    path = make_url(url).database
    return None if not path or path == ":memory:" or path.startswith("file::memory:") else path


def head_revision() -> str:
    """Latest Alembic revision id (tests compare the database against it)."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    cfg = Config(); cfg.set_main_option("script_location", os.path.normpath(MIGRATIONS_DIR))
    return ScriptDirectory.from_config(cfg).get_current_head()
