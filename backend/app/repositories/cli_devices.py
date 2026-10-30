from typing import Optional
from sqlalchemy import select, update
from ..models import CliDevice
from ..models.database import Database


class CliDeviceRepository:
    def __init__(self, db: Database): self.db = db

    def add(self, row: CliDevice) -> CliDevice:
        with self.db.session() as s:
            s.add(row); s.commit(); return row

    def by_device_hash(self, device_hash: str) -> Optional[CliDevice]:
        with self.db.session() as s:
            return s.scalars(select(CliDevice).where(CliDevice.device_hash == device_hash)).first()

    def by_user_code_hash(self, user_code_hash: str) -> Optional[CliDevice]:
        with self.db.session() as s:
            return s.scalars(select(CliDevice).where(CliDevice.user_code_hash == user_code_hash)).first()

    def set_fields(self, did: str, **values) -> None:
        with self.db.session() as s:
            s.execute(update(CliDevice).where(CliDevice.id == did).values(**values)); s.commit()

    def take_secret(self, did: str) -> Optional[str]:
        """Return the secret once. A second caller sees None."""
        with self.db.session() as s:
            row = s.get(CliDevice, did)
            if row is None or not row.secret: return None
            secret = row.secret
            n = s.execute(update(CliDevice).where(CliDevice.id == did, CliDevice.secret == secret).values(secret=None)).rowcount
            if n != 1:
                s.rollback(); return None
            s.commit()
            return secret
