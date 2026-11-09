"""Template library. Thin HTTP layer over TemplateService."""
from typing import Any, Literal, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from ..deps import current_user, limit_body, template_service

router = APIRouter(prefix="/api/templates", tags=["templates"])
Scope = Literal["user", "org"]


class SaveAs(BaseModel):
    workflow_id: str
    name: str = Field(max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    scope: Scope = "user"


class ImportIn(BaseModel):
    file: Any
    scope: Scope = "user"


class UseIn(BaseModel):
    name: Optional[str] = Field(None, max_length=200)


@router.get("")
def list_templates(user=Depends(current_user), svc=Depends(template_service)): return svc.list(user["id"])

@router.post("")
def save_as(body: SaveAs, user=Depends(current_user), svc=Depends(template_service)):
    return svc.save_from_workflow(user["id"], body.workflow_id, body.name, body.description, body.scope)

@router.post("/import", dependencies=[Depends(limit_body)])
def import_template(body: ImportIn, user=Depends(current_user), svc=Depends(template_service)): return svc.import_file(user["id"], body.file, body.scope)

@router.get("/{tid}/export")
def export_template(tid: str, user=Depends(current_user), svc=Depends(template_service)): return svc.export(tid, user["id"])

@router.post("/{tid}/use")
def use_template(tid: str, body: UseIn | None = None, user=Depends(current_user), svc=Depends(template_service)):
    return svc.use(tid, user["id"], body.name if body else None)

@router.delete("/{tid}")
def delete_template(tid: str, user=Depends(current_user), svc=Depends(template_service)): return svc.delete(tid, user["id"])
