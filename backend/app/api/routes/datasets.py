from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from ...schemas.dataset import (
    DatasetColumnUpdate, DatasetCreate, DatasetGrantInput, DatasetTokenInput, DatasetRowIn, DatasetRowQuery, DatasetRowUpdate, DatasetRowUpsert, DatasetUpdate,
)
from ..deps import current_user, dataset_access_service, dataset_row_service, dataset_service

router = APIRouter(prefix="/api/datasets", tags=["datasets"])
Revision = Annotated[int | None, Query(ge=1)]


@router.get("")
def list_datasets(limit: Annotated[int, Query(ge=1, le=100)] = 50,
                  offset: Annotated[int, Query(ge=0)] = 0,
                  user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.list(user["id"], limit, offset)


@router.post("", status_code=201)
def create_dataset(body: DatasetCreate, user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.create(user["id"], **body.model_dump())


@router.get("/{dataset_id}/access")
def dataset_access(dataset_id: str, user=Depends(current_user), svc=Depends(dataset_access_service)):
    return svc.list(user["id"], dataset_id)


@router.get("/{dataset_id}/access/grants/{workflow_id}")
def dataset_grant_status(dataset_id: str, workflow_id: str, user=Depends(current_user), svc=Depends(dataset_access_service)):
    return svc.grant_status(user["id"], dataset_id, workflow_id)


@router.put("/{dataset_id}/access/grants/{workflow_id}")
def grant_dataset(dataset_id: str, workflow_id: str, body: DatasetGrantInput,
                  user=Depends(current_user), svc=Depends(dataset_access_service)):
    return svc.grant(user["id"], dataset_id, workflow_id, body.permission)


@router.delete("/{dataset_id}/access/grants/{workflow_id}")
def revoke_dataset_grant(dataset_id: str, workflow_id: str,
                         user=Depends(current_user), svc=Depends(dataset_access_service)):
    return svc.revoke_grant(user["id"], dataset_id, workflow_id)


@router.post("/{dataset_id}/access/tokens", status_code=201)
def issue_dataset_token(dataset_id: str, body: DatasetTokenInput, response: Response,
                        user=Depends(current_user), svc=Depends(dataset_access_service)):
    response.headers["Cache-Control"] = "no-store"
    return svc.issue(user["id"], dataset_id, body.name, body.permission)


@router.post("/{dataset_id}/access/tokens/{token_id}/rotate")
def rotate_dataset_token(dataset_id: str, token_id: str, response: Response,
                         user=Depends(current_user), svc=Depends(dataset_access_service)):
    response.headers["Cache-Control"] = "no-store"
    return svc.rotate(user["id"], dataset_id, token_id)


@router.delete("/{dataset_id}/access/tokens/{token_id}")
def revoke_dataset_token(dataset_id: str, token_id: str,
                         user=Depends(current_user), svc=Depends(dataset_access_service)):
    return svc.revoke_token(user["id"], dataset_id, token_id)


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.get(user["id"], dataset_id)


@router.put("/{dataset_id}")
def update_dataset(dataset_id: str, body: DatasetUpdate, user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.update(user["id"], dataset_id, **body.model_dump())


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, revision: Revision = None,
                   user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.delete(user["id"], dataset_id, revision)


@router.post("/{dataset_id}/columns", status_code=201)
def add_column(dataset_id: str, body: DatasetColumnUpdate, user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.add_column(user["id"], dataset_id, **body.model_dump())


@router.put("/{dataset_id}/columns/{key}")
def update_column(dataset_id: str, key: str, body: DatasetColumnUpdate,
                  user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.update_column(user["id"], dataset_id, key, **body.model_dump())


@router.delete("/{dataset_id}/columns/{key}")
def remove_column(dataset_id: str, key: str, revision: Revision = None,
                  user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.remove_column(user["id"], dataset_id, key, revision)


@router.post("/{dataset_id}/rows/query")
def query_rows(dataset_id: str, body: DatasetRowQuery, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.query(user["id"], dataset_id, **body.model_dump())


@router.post("/{dataset_id}/rows", status_code=201)
def insert_row(dataset_id: str, body: DatasetRowIn, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.save(user["id"], dataset_id, **body.model_dump())


@router.post("/{dataset_id}/rows/upsert")
def upsert_row(dataset_id: str, body: DatasetRowUpsert, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.save(user["id"], dataset_id, **body.model_dump())


@router.get("/{dataset_id}/rows/{row_id}")
def get_row(dataset_id: str, row_id: str, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.get(user["id"], dataset_id, row_id)


@router.patch("/{dataset_id}/rows/{row_id}")
def update_row(dataset_id: str, row_id: str, body: DatasetRowUpdate, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.save(user["id"], dataset_id, row_id=row_id, **body.model_dump())


@router.delete("/{dataset_id}/rows/{row_id}")
def delete_row(dataset_id: str, row_id: str, revision: Revision = None,
               user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.delete(user["id"], dataset_id, row_id, revision)
