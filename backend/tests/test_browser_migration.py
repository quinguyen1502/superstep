"""Schema round trips preserve existing users on SQLite and disposable Postgres."""
import os
import uuid

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, select

from app.models import User
from app.models.database import Database, MIGRATIONS_DIR
from app.repositories.browser_artifacts import BrowserArtifactRepository
from app.services.browser_artifact_service import BrowserArtifactService
from tests.test_browser_runtime import PNG, context
from tests.test_db_postgres import fresh_pg, URL


def round_trip(db):
    cfg = Config(); cfg.set_main_option("script_location", os.path.normpath(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db.url.replace("%", "%%"))
    command.upgrade(cfg, "0054_chat_regenerate")
    owner = "browser-" + uuid.uuid4().hex
    with db.session() as session:
        session.add(User(id=owner, email=owner + "@example.test", active=True)); session.commit()
    command.upgrade(cfg, "head")
    service = BrowserArtifactService(BrowserArtifactRepository(db), clock=lambda: 1000)
    artifact = service.save(owner, context(owner), PNG)
    assert service.read(artifact, owner) == PNG
    command.downgrade(cfg, "0054_chat_regenerate")
    assert "browser_artifacts" not in inspect(db.engine).get_table_names()
    command.upgrade(cfg, "head")
    assert "browser_artifacts" in inspect(db.engine).get_table_names()
    assert BrowserArtifactRepository(db).owned(artifact, owner, 1000) is None
    with db.session() as session: assert session.scalar(select(User.id).where(User.id == owner)) == owner


def test_browser_artifact_sqlite_round_trip(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'browser.db'}")
    try: round_trip(db)
    finally: db.engine.dispose()


@pytest.mark.skipif(not URL.startswith("postgresql"), reason="requires disposable TEST_DATABASE_URL")
def test_browser_artifact_postgres_round_trip(fresh_pg): round_trip(fresh_pg)
