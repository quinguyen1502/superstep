from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Query, Response

from ...core.errors import AppError
from ...schemas.dataset import (
    DatasetBatchUpdate, DatasetColumnUpdate, DatasetConnectedInput, DatasetCreate, DatasetCsvInput, DatasetGrantInput, DatasetTokenInput,
    DatasetOwnerUpdate, DatasetRowIn, DatasetGroupedRowQuery, DatasetGroupsQuery, DatasetGroupRowsQuery, DatasetRowUpdate, DatasetRowUpsert, DatasetSummaryQuery, DatasetUpdate,
)
from ..deps import current_user, dataset_access_service, dataset_connected_service, dataset_csv_service, dataset_row_service, dataset_service, limit_body

router = APIRouter(prefix="/api/datasets", tags=["datasets"])
Revision = Annotated[int, Query(ge=1)]  # deletes always name the revision they saw


@router.get("")
def list_datasets(limit: Annotated[int, Query(ge=1, le=100)] = 50,
                  offset: Annotated[int, Query(ge=0)] = 0,
                  user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.list(user["id"], limit, offset)


@router.post("", status_code=201)
def create_dataset(body: DatasetCreate, user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.create(user["id"], **body.model_dump())


@router.post("/csv/preview")
def preview_csv(body: DatasetCsvInput, user=Depends(current_user), svc=Depends(dataset_csv_service)):
    return svc.preview(user["id"], **body.model_dump())


@router.post("/csv/import")
def import_csv(body: DatasetCsvInput, user=Depends(current_user), svc=Depends(dataset_csv_service)):
    return svc.import_csv(user["id"], **body.model_dump())


@router.get("/{dataset_id}/access")
def dataset_access(dataset_id: str, user=Depends(current_user), svc=Depends(dataset_access_service)):
    return svc.list(user["id"], dataset_id)


@router.get("/{dataset_id}/access/grants/{workflow_id}")
def dataset_grant_status(dataset_id: str, workflow_id: str, user=Depends(current_user), svc=Depends(dataset_access_service)):
    return svc.grant_status(user["id"], dataset_id, workflow_id)


@router.put("/{dataset_id}/access/grants/{workflow_id}")
def grant_dataset(dataset_id: str, workflow_id: str, body: DatasetGrantInput,
                  user=Depends(current_user), svc=Depends(dataset_access_service)):
    return svc.grant(user["id"], dataset_id, workflow_id, body.permission, body.allow_delete)


@router.delete("/{dataset_id}/access/grants/{workflow_id}")
def revoke_dataset_grant(dataset_id: str, workflow_id: str,
                         user=Depends(current_user), svc=Depends(dataset_access_service)):
    return svc.revoke_grant(user["id"], dataset_id, workflow_id)


@router.post("/{dataset_id}/access/tokens", status_code=201)
def issue_dataset_token(dataset_id: str, body: DatasetTokenInput, response: Response,
                        user=Depends(current_user), svc=Depends(dataset_access_service)):
    response.headers["Cache-Control"] = "no-store"
    return svc.issue(user["id"], dataset_id, body.name, body.permission, body.allow_delete)


@router.post("/{dataset_id}/access/tokens/{token_id}/rotate")
def rotate_dataset_token(dataset_id: str, token_id: str, response: Response,
                         user=Depends(current_user), svc=Depends(dataset_access_service)):
    response.headers["Cache-Control"] = "no-store"
    return svc.rotate(user["id"], dataset_id, token_id)


@router.delete("/{dataset_id}/access/tokens/{token_id}")
def revoke_dataset_token(dataset_id: str, token_id: str,
                         user=Depends(current_user), svc=Depends(dataset_access_service)):
    return svc.revoke_token(user["id"], dataset_id, token_id)


@router.get("/{dataset_id}/csv")
def export_csv(dataset_id: str, user=Depends(current_user), svc=Depends(dataset_csv_service)):
    name, content = svc.export(user["id"], dataset_id)
    filename = quote(f"{name}.csv", safe="")
    return Response(content, media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
        "Cache-Control": "no-store",
    })


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.get(user["id"], dataset_id)


@router.put("/{dataset_id}")
def update_dataset(dataset_id: str, body: DatasetUpdate, user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.update(user["id"], dataset_id, **body.model_dump())


@router.put("/{dataset_id}/owner")
def transfer_dataset(dataset_id: str, body: DatasetOwnerUpdate, user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.transfer(user["id"], dataset_id, **body.model_dump())


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, revision: Revision,
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
def remove_column(dataset_id: str, key: str, revision: Revision,
                  user=Depends(current_user), svc=Depends(dataset_service)):
    return svc.remove_column(user["id"], dataset_id, key, revision)


@router.post("/{dataset_id}/connected", dependencies=[Depends(limit_body)])
def execute_connected(dataset_id: str, body: DatasetConnectedInput, response: Response,
                      authorization: Annotated[str | None, Header()] = None,
                      svc=Depends(dataset_connected_service)):
    if authorization is None:
        raise AppError("AUTH_REQUIRED")
    scheme, _, secret = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise AppError("AUTH_TOKEN_INVALID")
    response.headers["Cache-Control"] = "no-store"
    return svc.execute(dataset_id, secret, body)


@router.post("/{dataset_id}/rows/query")
def query_rows(dataset_id: str, body: DatasetGroupedRowQuery, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.query(user["id"], dataset_id, include_total=True, **body.model_dump())


@router.post("/{dataset_id}/rows/groups")
def list_row_groups(dataset_id: str, body: DatasetGroupsQuery, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.groups(user["id"], dataset_id, **body.model_dump())


@router.post("/{dataset_id}/rows/groups/query")
def query_row_group(dataset_id: str, body: DatasetGroupRowsQuery, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.query(user["id"], dataset_id, include_total=True, **body.model_dump())


@router.post("/{dataset_id}/rows/summary")
def summarize_rows(dataset_id: str, body: DatasetSummaryQuery, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.summarize(user["id"], dataset_id, **body.model_dump())


@router.post("/{dataset_id}/rows", status_code=201)
def insert_row(dataset_id: str, body: DatasetRowIn, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.save(user["id"], dataset_id, **body.model_dump())


@router.post("/{dataset_id}/rows/upsert")
def upsert_row(dataset_id: str, body: DatasetRowUpsert, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.save(user["id"], dataset_id, **body.model_dump())


@router.get("/{dataset_id}/rows/{row_id}")
def get_row(dataset_id: str, row_id: str, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.get(user["id"], dataset_id, row_id)


@router.patch("/{dataset_id}/rows/batch", dependencies=[Depends(limit_body)])
def batch_update_rows(dataset_id: str, body: DatasetBatchUpdate, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.batch_update(user["id"], dataset_id, **body.model_dump())


@router.patch("/{dataset_id}/rows/{row_id}")
def update_row(dataset_id: str, row_id: str, body: DatasetRowUpdate, user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.save(user["id"], dataset_id, row_id=row_id, **body.model_dump())


@router.delete("/{dataset_id}/rows/{row_id}")
def delete_row(dataset_id: str, row_id: str, revision: Revision,
               user=Depends(current_user), svc=Depends(dataset_row_service)):
    return svc.delete(user["id"], dataset_id, row_id, revision)
