from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request

from ...core.client_ip import client_ip
from ...core.errors import AppError
from ...schemas.dataset_shares import DatasetShareInput, DatasetSharePage, DatasetSharePagination, DatasetSharePreview
from ...services.dataset_shares import DatasetShareService, PublicRead
from ..dataset_share_http import DATASET_SHARE_HEADER, PUBLIC_DATASET_VIEW
from ..deps import current_user, dataset_share_service

router = APIRouter(prefix="/api/datasets/{dataset_id}/shares", tags=["datasets"])
public_router = APIRouter(prefix=PUBLIC_DATASET_VIEW, tags=["public dataset view"])
Service = Annotated[DatasetShareService, Depends(dataset_share_service)]
User = Annotated[dict, Depends(current_user)]


@router.get("")
def list_shares(dataset_id: str, page: Annotated[DatasetSharePagination, Query()], user: User, service: Service):
    return service.list(user["id"], dataset_id, page.limit, page.offset)


@router.post("", status_code=201)
def create_share(dataset_id: str, body: DatasetShareInput, user: User, service: Service):
    return service.create(user["id"], dataset_id, **body.model_dump())


@router.post("/preview")
def preview_share(dataset_id: str, body: DatasetSharePreview, user: User, service: Service):
    return service.preview(user["id"], dataset_id, **body.model_dump())


@router.post("/{share_id}/rotate")
def rotate_share(dataset_id: str, share_id: str, user: User, service: Service):
    return service.rotate(user["id"], dataset_id, share_id)


@router.delete("/{share_id}")
def revoke_share(dataset_id: str, share_id: str, user: User, service: Service):
    return service.revoke(user["id"], dataset_id, share_id)


async def public_read(request: Request, service: Service,
                      credentials: Annotated[list[str] | None, Header(alias=DATASET_SHARE_HEADER)] = None) -> PublicRead:
    peer = request.client.host if request.client else None
    ip = client_ip(peer, request.headers.get("x-forwarded-for"))
    return await service.authorize(credentials[0] if credentials and len(credentials) == 1 else "", ip)


Share = Annotated[PublicRead, Depends(public_read)]


@public_router.get("")
def read_view(request: Request, share: Share):
    if request.query_params:
        raise AppError("BAD_REQUEST")
    return share.view.metadata()


@public_router.get("/rows")
def read_rows(share: Share, page: Annotated[DatasetSharePage, Query()], service: Service):
    return service.read_rows(share, **page.model_dump())
