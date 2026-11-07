from sqlalchemy import delete, select
from ..models import BrowserArtifact


class BrowserArtifactRepository:
    def __init__(self, db): self.db = db

    def add(self, row):
        with self.db.session() as session:
            session.add(row); session.commit()

    def owned(self, artifact_id, owner, now):
        with self.db.session() as session:
            return session.scalar(select(BrowserArtifact).where(BrowserArtifact.id == artifact_id,
                BrowserArtifact.owner == owner, BrowserArtifact.expires > now))

    def sweep(self, now):
        with self.db.session() as session:
            count = session.execute(delete(BrowserArtifact).where(BrowserArtifact.expires <= now)).rowcount
            session.commit(); return count
