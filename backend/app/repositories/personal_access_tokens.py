from typing import Optional
from sqlalchemy import select, update
from ..models import PersonalAccessToken
from ..models.database import Database


class PersonalAccessTokenRepository:
    def __init__(self, db: Database): self.db = db

    def add(self, row: PersonalAccessToken) -> PersonalAccessToken:
        with self.db.session() as s:
            s.add(row); s.commit(); return row

    def get(self, tid: str) -> Optional[PersonalAccessToken]:
        with self.db.session() as s:
            return s.get(PersonalAccessToken, tid)

    def by_hash(self, token_hash: str) -> Optional[PersonalAccessToken]:
        with self.db.session() as s:
            return s.scalars(select(PersonalAccessToken).where(PersonalAccessToken.token_hash == token_hash)).first()

    def active_by_name(self, user_id: str, name: str) -> Optional[PersonalAccessToken]:
        with self.db.session() as s:
            return s.scalars(select(PersonalAccessToken).where(
                PersonalAccessToken.user_id == user_id, PersonalAccessToken.name == name,
                PersonalAccessToken.revoked.is_(None))).first()

    def list_active(self, user_id: str) -> list[PersonalAccessToken]:
        with self.db.session() as s:
            return list(s.scalars(select(PersonalAccessToken).where(
                PersonalAccessToken.user_id == user_id, PersonalAccessToken.revoked.is_(None)).order_by(PersonalAccessToken.created.desc())))

    def set_fields(self, tid: str, **values) -> None:
        with self.db.session() as s:
            s.execute(update(PersonalAccessToken).where(PersonalAccessToken.id == tid).values(**values)); s.commit()
