from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..core import permissions as P
from ..core.dataset_formula import Formula, materialize_formulas
from ..core.dataset_types import MAX_ROW_BYTES, TEXT_KINDS, dataset_size, key_digest
from ..core.dataset_rules import violates_rule
from ..core.errors import AppError
from ..models.database import Database
from ..models.dataset import Dataset, DatasetColumn, DatasetRelationEdge, DatasetRow, DatasetRowKey
from ..models.dataset_access import DatasetApiToken, DatasetWorkflowGrant
from ..models.dataset_receipt import DatasetWriteReceipt
from ..models.dataset_share import DatasetShare
from ..models.team import TeamMember
from ..models.user import User
from ..models.workflow import Workflow

UNIQUE_SAMPLE_ROWS = 5
KEY_BATCH = 500
CLEAR_BATCH = 500


@dataclass(frozen=True)
class RowChange:
    """One field changed on every row with the definition: cleared, or filled with a default."""
    field: str
    clear: bool = False
    value: object = None
    auto_number: bool = False


def delete_dataset_definitions(session: Session, condition) -> None:
    """Clean up definitions explicitly on SQLite as well as on PostgreSQL."""
    if session.get_bind().dialect.name == "postgresql":
        lock = select(Dataset.id).where(condition).order_by(Dataset.id).with_for_update()
    else:
        lock = update(Dataset).where(condition).values(revision=Dataset.revision).returning(Dataset.id)
    ids = list(session.scalars(lock))
    if not ids:
        return
    external_definition = select(DatasetColumn.key).where(
        DatasetColumn.relation_target_id.in_(ids), DatasetColumn.dataset_id.not_in(ids),
        DatasetColumn.archived.is_(False),
    ).exists()
    external_edge = select(DatasetRelationEdge.field).where(
        DatasetRelationEdge.target_dataset_id.in_(ids), DatasetRelationEdge.source_dataset_id.not_in(ids),
    ).exists()
    if session.scalar(select(external_definition | external_edge)):
        raise AppError("DATASET_RELATION_REFERENCED")
    session.execute(delete(DatasetRelationEdge).where(DatasetRelationEdge.source_dataset_id.in_(ids)))
    session.execute(delete(DatasetShare).where(DatasetShare.dataset_id.in_(ids)))
    session.execute(delete(DatasetWriteReceipt).where(DatasetWriteReceipt.dataset_id.in_(ids)))
    session.execute(delete(DatasetApiToken).where(DatasetApiToken.dataset_id.in_(ids)))
    session.execute(delete(DatasetWorkflowGrant).where(DatasetWorkflowGrant.dataset_id.in_(ids)))
    session.execute(delete(DatasetRowKey).where(DatasetRowKey.dataset_id.in_(ids)))
    session.execute(delete(DatasetRow).where(DatasetRow.dataset_id.in_(ids)))
    session.execute(delete(DatasetColumn).where(DatasetColumn.dataset_id.in_(ids)))
    session.execute(delete(Dataset).where(Dataset.id.in_(ids)))


class DatasetRepository:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _visible(uid: str):
        teams = select(TeamMember.team_id).where(TeamMember.user_id == uid)
        return (Dataset.owner_id == uid) | Dataset.team_id.in_(teams)

    def list(self, uid: str, limit: int, offset: int) -> list[Dataset]:
        query = (
            select(Dataset).where(self._visible(uid))
            .order_by(Dataset.name_key, Dataset.id).limit(limit).offset(offset)
        )
        with self.db.session() as session:
            return list(session.scalars(query))

    def get(self, uid: str, dataset_id: str) -> Dataset | None:
        query = (
            select(Dataset).options(joinedload(Dataset.columns))
            .where(Dataset.id == dataset_id, self._visible(uid))
        )
        with self.db.session() as session:
            return session.scalars(query).unique().one_or_none()

    def revisions(self, uid: str, dataset_id: str) -> tuple[int, int] | None:
        statement = select(Dataset.revision, Dataset.data_revision).where(Dataset.id == dataset_id, self._visible(uid))
        with self.db.session() as session:
            row = session.execute(statement).one_or_none()
            return (row.revision, row.data_revision) if row is not None else None

    @staticmethod
    def advance_data_revision(session: Session, dataset_id: str) -> None:
        """Advance the persisted marker under the caller's dataset writer lock."""
        session.get(Dataset, dataset_id).data_revision += 1

    @staticmethod
    def raise_integrity_error(exc: IntegrityError) -> None:
        detail = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if detail in {"uq_datasets_owner_name", "uq_datasets_team_name"} or any(
            f"UNIQUE constraint failed: datasets.{scope}, datasets.name_key" in str(exc.orig)
            for scope in ("owner_id", "team_id")
        ):
            raise AppError("DATASET_NAME_TAKEN") from exc
        raise exc

    def _commit(self, session: Session) -> None:
        try:
            session.commit()
        except IntegrityError as exc:
            self.raise_integrity_error(exc)

    def add(self, dataset: Dataset) -> Dataset:
        relations = [column for column in dataset.columns if column.kind == "relation"]
        with self.db.session() as session:
            if relations:
                self.lock_relations(session, dataset.owner_id or dataset.team_owner_id, dataset, relations, manage=True)
            session.add(dataset)
            self._commit(session)
        return dataset

    def lock(self, session: Session, uid: str, dataset_id: str, revision: int, *, advance: bool = False) -> None:
        """Serialize writers on both engines and check the schema and membership at the write boundary."""
        result = session.execute(
            update(Dataset).where(
                Dataset.id == dataset_id, Dataset.revision == revision, self._visible(uid),
            ).values(revision=revision + int(advance))
        )
        if result.rowcount != 1:
            raise AppError("DATASET_SCHEMA_CONFLICT")

    def lock_relations(self, session: Session, uid: str, source: Dataset, relations: list[DatasetColumn], *,
                       revision: int | None = None, advance: bool = False, manage: bool = False) -> None:
        """Lock all participating Datasets before checking current access, scope and display fields."""
        targets = {column.relation_target_id for column in relations}
        if source.id in targets or None in targets:
            raise AppError("DATASET_RELATION_TARGET_INVALID")
        for dataset_id in sorted(targets | ({source.id} if revision is not None else set())):
            if dataset_id == source.id:
                self.lock(session, uid, source.id, revision, advance=advance)
            else:
                locked = session.execute(update(Dataset).where(Dataset.id == dataset_id, self._visible(uid))
                                         .values(revision=Dataset.revision))
                if locked.rowcount != 1:
                    raise AppError("DATASET_RELATION_TARGET_INVALID")
        role = session.scalar(select(User.role).where(User.id == uid, User.active.is_(True)).with_for_update(read=True))
        if not P.can(role, P.RESOURCES_MANAGE):
            raise AppError("PERMISSION_DENIED", permission=P.RESOURCES_MANAGE)
        if source.team_id is not None and session.scalar(select(TeamMember.user_id).where(
            TeamMember.team_id == source.team_id, TeamMember.user_id == uid,
        ).with_for_update(read=True)) is None:
            raise AppError("DATASET_NOT_FOUND")
        current = session.get(Dataset, source.id) if revision is not None else source
        if manage and not current.may_manage(uid, role):
            raise AppError("DATASET_MANAGE_DENIED")
        for column in relations:
            target = session.get(Dataset, column.relation_target_id)
            display = session.get(DatasetColumn, (column.relation_target_id, column.relation_display_key))
            if not source.same_scope(target) or display is None or display.archived or display.kind not in TEXT_KINDS:
                raise AppError("DATASET_RELATION_TARGET_INVALID")

    @staticmethod
    def _check_display_column(session: Session, dataset_id: str, key: str) -> None:
        referenced = select(DatasetColumn.key).where(
            DatasetColumn.relation_target_id == dataset_id, DatasetColumn.relation_display_key == key,
            DatasetColumn.archived.is_(False),
        ).limit(1)
        if session.scalar(referenced) is not None:
            raise AppError("DATASET_RELATION_REFERENCED")

    def save(self, uid: str, dataset: Dataset, revision: int, *, require_empty: bool = False,
             unique: tuple[str, bool] | None = None, rows: RowChange | None = None,
             validate_field: str | None = None, formulas: dict[str, Formula] | None = None,
             relation: DatasetColumn | None = None) -> tuple[Dataset, int]:
        """Save a definition under the writer lock and return it with the number of rows changed.

        `rows` clears or fills one field on every row, and `unique` adds or drops one column's row keys,
        both in the same transaction as the definition. A supplied formula plan also backfills\n        results and diagnostics, including clearing a removed computed field."""
        with self.db.session() as session:
            if relation is None:
                self.lock(session, uid, dataset.id, revision, advance=True)
            else:
                self.lock_relations(session, uid, dataset, [relation], revision=revision, advance=True, manage=True)
            if rows is not None and rows.clear:
                self._check_display_column(session, dataset.id, rows.field)
                session.execute(delete(DatasetRelationEdge).where(
                    DatasetRelationEdge.source_dataset_id == dataset.id, DatasetRelationEdge.field == rows.field,
                ))
            if require_empty and session.scalar(select(DatasetRow.id).where(DatasetRow.dataset_id == dataset.id).limit(1)):
                raise AppError("DATASET_SCHEMA_HAS_ROWS")
            dataset.revision = revision + 1
            current = session.get(Dataset, dataset.id)
            dataset.auto_number_counter = current.auto_number_counter
            dataset.data_revision = current.data_revision
            result = session.merge(dataset)
            session.flush()
            changed = 0
            if formulas is not None:
                changed = self._backfill_formulas(session, dataset.id, formulas, clear=rows.field if rows and rows.clear else None)
            elif rows is not None:
                if rows.auto_number:
                    changed = self._backfill_auto_numbers(session, dataset.id, rows.field)
                elif rows.clear:
                    changed = self._clear_field(session, dataset.id, rows.field)
                else:
                    changed = self._fill_field(session, dataset.id, rows)
            if unique is not None:
                field, enabled = unique
                if enabled:
                    self._backfill_keys(session, dataset.id, field)
                else:
                    session.execute(delete(DatasetRowKey).where(
                        DatasetRowKey.dataset_id == dataset.id, DatasetRowKey.field == field,
                    ))
            if validate_field:
                self._validate_rows(session, result, validate_field)
            self.advance_data_revision(session, dataset.id)
            self._commit(session)
            return result, changed

    @staticmethod
    def _backfill_formulas(session: Session, dataset_id: str, formulas: dict[str, Formula], *, clear: str | None) -> int:
        base = select(DatasetRow).where(DatasetRow.dataset_id == dataset_id).order_by(DatasetRow.id).limit(KEY_BATCH)
        offset, changed = "", 0
        while page := list(session.scalars(base.where(DatasetRow.id > offset))):
            for row in page:
                inputs = row.values
                if clear is not None and clear in inputs:
                    inputs = dict(inputs)
                    del inputs[clear]
                values, errors = materialize_formulas(formulas, inputs)
                if dataset_size(values) > MAX_ROW_BYTES:
                    raise AppError("DATASET_ROW_TOO_LARGE", max=MAX_ROW_BYTES)
                if values != row.values or errors != row.formula_errors:
                    row.values, row.formula_errors = values, errors
                    row.revision += 1
                    changed += 1
            offset = page[-1].id
            session.flush()
        return changed

    @staticmethod
    def _validate_rows(session: Session, dataset: Dataset, field: str) -> None:
        column = next(column for column in dataset.columns if column.key == field)
        statement = select(DatasetRow.id, DatasetRow.values).where(DatasetRow.dataset_id == dataset.id)
        statement = statement.order_by(DatasetRow.created, DatasetRow.id).execution_options(yield_per=256)
        count, sample = 0, []
        for row_id, values in session.execute(statement):
            if violates_rule(values.get(field), column.validation_rules):
                count += 1
                if len(sample) < 5:
                    sample.append(row_id)
        if count:
            raise AppError("DATASET_COLUMN_RULE_EXISTING_ROWS", field=field, count=count,
                           details={"field": field, "count": count, "sample_row_ids": sample})

    @staticmethod
    def reserve_auto_numbers(session: Session, dataset_id: str, count: int) -> int:
        """The caller holds the dataset writer lock for this transaction."""
        counter = session.get(Dataset, dataset_id)
        first = counter.auto_number_counter + 1
        counter.auto_number_counter += count
        return first

    def _backfill_auto_numbers(self, session: Session, dataset_id: str, field: str) -> int:
        rows = list(session.scalars(select(DatasetRow).where(DatasetRow.dataset_id == dataset_id)
                                    .order_by(DatasetRow.created, DatasetRow.id)))
        first = self.reserve_auto_numbers(session, dataset_id, len(rows))
        for index, row in enumerate(rows, first):
            row.values = {**row.values, field: index}
            row.revision += 1
        session.flush()
        return len(rows)

    @staticmethod
    def _clear_field(session: Session, dataset_id: str, field: str) -> int:
        """Remove a field from every row in batches. Returns the number of rows that held it."""
        if session.get_bind().dialect.name == "postgresql":
            statement = text(
                'UPDATE dataset_rows SET "values" = "values" - CAST(:field AS text) WHERE dataset_id = :dataset AND id IN ('
                'SELECT id FROM dataset_rows WHERE dataset_id = :dataset AND jsonb_exists("values", :field) LIMIT :batch)'
            )
        else:
            statement = text(
                'UPDATE dataset_rows SET "values" = json_remove("values", :path) WHERE dataset_id = :dataset AND id IN ('
                'SELECT id FROM dataset_rows WHERE dataset_id = :dataset AND json_type("values", :path) IS NOT NULL LIMIT :batch)'
            )
        params = {"dataset": dataset_id, "field": field, "path": f'$."{field}"', "batch": CLEAR_BATCH}
        total = 0
        while True:
            count = session.execute(statement, params).rowcount
            total += count
            if count < CLEAR_BATCH:
                return total

    @staticmethod
    def _fill_field(session: Session, dataset_id: str, change: RowChange) -> int:
        """Write a default into every row after checking that no row would pass the byte limit."""
        extra = dataset_size({change.field: change.value}) - 1
        sizes = select(DatasetRow.values).where(DatasetRow.dataset_id == dataset_id).execution_options(yield_per=KEY_BATCH)
        for values in session.scalars(sizes):
            if dataset_size(values) + extra > MAX_ROW_BYTES:
                raise AppError("DATASET_ROW_TOO_LARGE", max=MAX_ROW_BYTES)
        if session.get_bind().dialect.name == "postgresql":
            statement = text(
                'UPDATE dataset_rows SET "values" = "values" || jsonb_build_object(CAST(:field AS text), CAST(:value AS jsonb)) '
                'WHERE dataset_id = :dataset'
            )
        else:
            statement = text('UPDATE dataset_rows SET "values" = json_set("values", :path, json(:value)) WHERE dataset_id = :dataset')
        return session.execute(statement, {
            "dataset": dataset_id, "field": change.field, "path": f'$."{change.field}"', "value": json.dumps(change.value),
        }).rowcount

    @staticmethod
    def _backfill_keys(session: Session, dataset_id: str, field: str) -> None:
        """Index every non-empty value of `field`, or fail with the duplicate count and sample rows."""
        statement = (
            select(DatasetRow.id, DatasetRow.values[field]).where(DatasetRow.dataset_id == dataset_id)
            .order_by(DatasetRow.created, DatasetRow.id).execution_options(yield_per=KEY_BATCH)
        )
        groups: dict[str, list[str]] = {}
        values: dict[str, object] = {}
        for row_id, value in session.execute(statement):
            if value is None:
                continue
            digest = key_digest(value)
            groups.setdefault(digest, []).append(row_id)
            values.setdefault(digest, value)
        duplicates = [(digest, ids) for digest, ids in groups.items() if len(ids) > 1]
        if duplicates:
            samples = [row_id for _, ids in duplicates for row_id in ids][:UNIQUE_SAMPLE_ROWS]
            raise AppError(
                "DATASET_UNIQUE_DUPLICATES", field=field, count=sum(len(ids) for _, ids in duplicates),
                values=len(duplicates), rows=samples, value=values[duplicates[0][0]],
            )
        keys = [{"dataset_id": dataset_id, "field": field, "value_hash": digest, "row_id": ids[0]}
                for digest, ids in groups.items()]
        for start in range(0, len(keys), KEY_BATCH):
            session.execute(insert(DatasetRowKey), keys[start:start + KEY_BATCH])

    def workflows_mentioning(self, dataset_id: str) -> list[tuple[str, str | None, str | None]]:
        """Saved workflows whose graph text mentions the dataset id, as (id, name, data)."""
        query = select(Workflow.id, Workflow.name, Workflow.data).where(Workflow.data.contains(f'"{dataset_id}"'))
        with self.db.session() as session:
            return [tuple(row) for row in session.execute(query)]

    def delete(self, uid: str, dataset_id: str, revision: int) -> None:
        with self.db.session() as session:
            self.lock(session, uid, dataset_id, revision, advance=True)
            delete_dataset_definitions(session, Dataset.id == dataset_id)
            session.commit()
