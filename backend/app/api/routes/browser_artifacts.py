from fastapi import APIRouter, Depends, Response
from ..deps import current_user, browser_artifact_service

router = APIRouter(prefix="/api/browser/artifacts", tags=["browser"])


@router.get("/{artifact_id}")
def screenshot(artifact_id: str, user=Depends(current_user), service=Depends(browser_artifact_service)):
    return Response(service.read(artifact_id, user["id"]), media_type="image/png", headers={
        "Cache-Control": "no-store", "Vary": "Authorization, Cookie", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox", "Content-Disposition": 'inline; filename="browser.png"'})
