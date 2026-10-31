"""Admin view and migration of chat attachment storage (TASK-0194, REQ-0080, DEC-0074)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from ..deps import attachment_migration, current_user

router = APIRouter(prefix="/api/admin/attachments", tags=["admin"])


class MigrateIn(BaseModel):
    to: str
    batch: int = Field(100, description="Files per batch (1 to 1000)")
    dry_run: bool = False
    limit: int | None = Field(None, ge=1, description="Stop after this many files; run again to continue")


@router.get("")
def summary(user=Depends(current_user), svc=Depends(attachment_migration)): return svc.require(user["id"]).summary()

@router.post("/migrate")
def migrate(body: MigrateIn, user=Depends(current_user), svc=Depends(attachment_migration)):
    return svc.require(user["id"]).run(body.to, body.batch, body.dry_run, body.limit)
