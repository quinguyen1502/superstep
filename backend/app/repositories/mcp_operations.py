from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from ..models import McpOperation
from ..models.database import Database


class McpOperationRepository:
    def __init__(self, db: Database): self.db = db

    def get(self, operation_id: str) -> Optional[McpOperation]:
        with self.db.session() as session: return session.get(McpOperation, operation_id)

    def reserve(self, row: McpOperation) -> tuple[McpOperation, bool]:
        with self.db.session() as session:
            try: session.add(row); session.commit(); return row, True
            except IntegrityError:
                session.rollback(); existing = session.get(McpOperation, row.id)
                if existing is None: raise
                return existing, False

    def finish(self, operation_id: str, status: str, result: Optional[str], now: float):
        with self.db.session() as session:
            session.execute(update(McpOperation).where(McpOperation.id == operation_id, McpOperation.status != "confirmed")
                            .values(status=status, result=result, updated=now)); session.commit()

    def list_for(self, server_id: str, owner: str) -> list[McpOperation]:
        with self.db.session() as session:
            return list(session.scalars(select(McpOperation).where(McpOperation.server_id == server_id, McpOperation.owner == owner)
                                        .order_by(McpOperation.created.desc()).limit(50)))
