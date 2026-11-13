"""Authorization contracts for saved workflows and dataset-scoped credentials."""
from dataclasses import dataclass
from secrets import token_urlsafe
from time import time
from uuid import uuid4

from ..core import permissions as P
from ..core.dataset_types import INVALID_TEXT
from ..core.errors import AppError
from ..models.dataset import Dataset
from ..models.dataset_access import DatasetApiToken, DatasetWorkflowGrant
from ..models.workflow import Workflow
from ..repositories.dataset_access import DatasetAccessRepository
from .dataset_service import DatasetService
from .pat_service import digest

TOKEN_PREFIX = "dsat_"
OPERATIONS = {"read", "write"}


@dataclass(frozen=True)
class DatasetPrincipal:
    dataset_id: str
    subject_id: str
    permission: str


def _allows(permission: str, operation: str) -> bool:
    return operation in OPERATIONS and permission in {operation, "read_write"}


def _token_payload(token: DatasetApiToken) -> dict:
    return {"id": token.id, "name": token.name, "permission": token.permission,
            "allow_delete": token.allow_delete, "prefix": token.prefix, "created": token.created}


class DatasetAccessService:
    def __init__(self, datasets: DatasetService, repo: DatasetAccessRepository):
        self.datasets, self.repo, self.access = datasets, repo, datasets.access

    def _in_scope(self, dataset: Dataset, workflow: Workflow) -> bool:
        owner = workflow.owner
        if owner is None or self.access.role(owner) is None:
            return False
        if dataset.team_id is None:
            return dataset.owner_id == owner
        teams = self.access.teams
        return dataset.team_id in teams.teams_of(owner) and any(
            share.team_id == dataset.team_id for share, _ in teams.shares_for_workflow(workflow.id)
        )

    def list(self, uid: str, dataset_id: str) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, None)
        return {
            "grants": [{"workflow_id": grant.workflow_id, "workflow_name": name, "permission": grant.permission,
                        "allow_delete": grant.allow_delete} for grant, name in self.repo.grants(dataset.id)],
            "workflows": [{"id": workflow.id, "name": workflow.name}
                          for workflow, _ in self.access.visible(uid)
                          if self.access.may(workflow.id, uid, P.SHARE) and self._in_scope(dataset, workflow)],
            "tokens": [_token_payload(token) for token in self.repo.tokens(dataset.id)],
        }

    def grant_status(self, uid: str, dataset_id: str, workflow_id: str) -> dict:
        dataset = self.datasets.definition(uid, dataset_id)
        workflow = self.access.workflow(workflow_id, uid, P.VIEW)
        grant = self.repo.grant(dataset.id, workflow.id) if self._in_scope(dataset, workflow) else None
        return {"permission": grant.permission if grant else None, "allow_delete": bool(grant and grant.allow_delete)}

    def grant(self, uid: str, dataset_id: str, workflow_id: str, permission: str, allow_delete: bool = False) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, None)
        workflow = self.access.workflow(workflow_id, uid, P.SHARE)
        if not self._in_scope(dataset, workflow):
            raise AppError("DATASET_GRANT_DENIED")
        self.repo.set_grant(uid, dataset, DatasetWorkflowGrant(
            dataset_id=dataset.id, workflow_id=workflow.id, permission=permission,
            allow_delete=allow_delete, created=time(),
        ))
        self.datasets.audit.record(uid, "dataset.grant", "dataset", dataset.id,
                                   workflow_id=workflow.id, permission=permission, allow_delete=allow_delete)
        return {"workflow_id": workflow.id, "workflow_name": workflow.name,
                "permission": permission, "allow_delete": allow_delete}

    def revoke_grant(self, uid: str, dataset_id: str, workflow_id: str) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, None)
        self.repo.revoke_grant(uid, dataset, workflow_id)
        self.datasets.audit.record(uid, "dataset.grant_revoke", "dataset", dataset.id, workflow_id=workflow_id)
        return {"ok": True}

    def issue(self, uid: str, dataset_id: str, name: str, permission: str, allow_delete: bool = False) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, None)
        name = name.strip()
        if not name or INVALID_TEXT.search(name):
            raise AppError("BAD_REQUEST")
        secret = TOKEN_PREFIX + token_urlsafe(32)
        token = DatasetApiToken(id=uuid4().hex, dataset_id=dataset.id, issuer_id=uid, name=name,
                                permission=permission, allow_delete=allow_delete, token_hash=digest(secret),
                                prefix=secret[:10], created=time())
        self.repo.add_token(uid, dataset, token)
        self.datasets.audit.record(uid, "dataset.token_issue", "dataset", dataset.id,
                                   token_id=token.id, permission=permission, allow_delete=allow_delete)
        return {**_token_payload(token), "token": secret}

    def rotate(self, uid: str, dataset_id: str, token_id: str) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, None)
        secret = TOKEN_PREFIX + token_urlsafe(32)
        token = self.repo.change_token(uid, dataset, token_id, issuer_id=uid, token_hash=digest(secret),
                                       prefix=secret[:10], created=time())
        self.datasets.audit.record(uid, "dataset.token_rotate", "dataset", dataset.id, token_id=token_id)
        return {**_token_payload(token), "token": secret}

    def revoke_token(self, uid: str, dataset_id: str, token_id: str) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, None)
        self.repo.change_token(uid, dataset, token_id, revoked=time())
        self.datasets.audit.record(uid, "dataset.token_revoke", "dataset", dataset.id, token_id=token_id)
        return {"ok": True}

    def workflow_dataset(self, caller_id: str, saved_workflow_id: str | None, dataset_id: str, operation: str,
                         *, public: bool = False, deleting: bool = False) -> tuple[Dataset, Workflow, DatasetWorkflowGrant]:
        if public or not saved_workflow_id:
            raise AppError("DATASET_GRANT_DENIED")
        workflow = self.access.workflow(saved_workflow_id, caller_id, P.RUN)
        grant = self.repo.grant(dataset_id, workflow.id)
        allowed = grant is not None and (grant.allow_delete if deleting else _allows(grant.permission, operation))
        if not allowed:
            raise AppError("DATASET_GRANT_DENIED")
        try:
            dataset = self.datasets.definition(workflow.owner, dataset_id)
        except AppError as exc:
            raise AppError("DATASET_GRANT_DENIED") from exc
        if not self._in_scope(dataset, workflow):
            raise AppError("DATASET_GRANT_DENIED")
        return dataset, workflow, grant

    def for_workflow(self, caller_id: str, saved_workflow_id: str | None, dataset_id: str, operation: str,
                     *, public: bool = False) -> DatasetPrincipal:
        dataset, workflow, grant = self.workflow_dataset(caller_id, saved_workflow_id, dataset_id, operation, public=public)
        return DatasetPrincipal(dataset.id, workflow.id, grant.permission)

    def token_dataset(self, secret: str, dataset_id: str, operation: str, *, deleting: bool = False) -> tuple[Dataset, DatasetApiToken]:
        if not secret.startswith(TOKEN_PREFIX) or len(secret) > 100:
            raise AppError("AUTH_TOKEN_INVALID")
        token = self.repo.token_for_hash(digest(secret))
        allowed = token is not None and (token.allow_delete if deleting else _allows(token.permission, operation))
        if token is None or token.dataset_id != dataset_id or not allowed:
            raise AppError("AUTH_TOKEN_INVALID")
        try:
            dataset = self.datasets.editable_definition(token.issuer_id, dataset_id, None)
        except AppError as exc:
            raise AppError("AUTH_TOKEN_INVALID") from exc
        return dataset, token

    def for_token(self, secret: str, dataset_id: str, operation: str) -> DatasetPrincipal:
        dataset, token = self.token_dataset(secret, dataset_id, operation)
        return DatasetPrincipal(dataset.id, token.id, token.permission)
