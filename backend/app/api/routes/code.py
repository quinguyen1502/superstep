"""Tool node Code mode: runtime facts for the editor and Test with sample state."""
from fastapi import APIRouter, Depends
from ...schemas.code import CodeTest
from ..deps import code_service, current_user, limit_body

router = APIRouter(prefix="/api", tags=["code"])

@router.get("/meta/runtime")
def runtime(user=Depends(current_user), svc=Depends(code_service)): return svc.runtime()

@router.post("/code/test", dependencies=[Depends(limit_body)])
async def test_code(body: CodeTest, user=Depends(current_user), svc=Depends(code_service)):
    return await svc.test(user["id"], body.source, body.state, body.node, body.timeout, body.language)
