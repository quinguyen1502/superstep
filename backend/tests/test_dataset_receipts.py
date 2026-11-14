from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, update

from app.core.errors import AppError
from app.models import Dataset, DatasetWriteReceipt, Run, User, Workflow
from app.models.database import MIGRATIONS_DIR
from app.repositories.dataset_rows import DatasetRowRepository, WorkflowWrite
from app.repositories.datasets import DatasetRepository
from app.repositories.runs import StaleLease
from test_dataset_rows import call
from test_datasets import client, create  # noqa: F401
from test_identity_migration import db, upgrade  # noqa: F401


@pytest.fixture
def writes(client, db):
    dataset = create(client, name="Receipts", columns=[{"key": "ticket", "label": "Ticket", "kind": "text", "unique": True}])
    with db.session() as session:
        session.add(Workflow(id="receipts-flow", name="Receipts", owner="owner"))
        session.add(Run(id="receipts-run", workflow_id="receipts-flow", lease_gen=1))
        session.commit()
    base = f"/api/datasets/{dataset['id']}"
    call(client, "PUT", f"{base}/access/grants/receipts-flow", body={"permission": "write"})
    repo = DatasetRowRepository(DatasetRepository(db))
    return repo, repo.datasets.get("owner", dataset["id"]), base


def write(repo, dataset, operation, ticket, fence=1):
    values = {"ticket": ticket}
    row, inserted, replayed, _ = repo.save("owner", dataset, lambda _: values, workflow=WorkflowWrite(
        run_id="receipts-run", workflow_id="receipts-flow", operation_id=operation,
        arguments={"operation": "insert", "values": values}, fence=fence,
    ))
    return row, inserted, replayed


def test_receipt_replays_current_row_after_commit_and_worker_takeover(client, db, writes):
    repo, dataset, base = writes
    with ThreadPoolExecutor(max_workers=2) as workers:
        replies = list(workers.map(lambda _: write(repo, dataset, "step#1", "A"), range(2)))
    row, inserted, _ = replies[0]
    assert inserted and replies[1][0].id == row.id
    call(client, "PATCH", f"{base}/rows/{row.id}", body={"revision": 1, "values": {"ticket": "Updated"}})
    with db.session() as session:
        run = session.get(Run, "receipts-run")
        run.lease_gen = 2
        session.commit()
    with pytest.raises(StaleLease):
        write(repo, dataset, "step#2", "B")
    replayed, _, reused = write(repo, dataset, "step#1", "A", fence=2)
    assert reused and replayed.id == row.id and replayed.values == {"ticket": "Updated"} and replayed.revision == 2
    with pytest.raises(AppError) as conflict:
        write(repo, dataset, "step#1", "B", fence=2)
    assert conflict.value.code == "DATASET_RECEIPT_CONFLICT"
    second, _, _ = write(repo, dataset, "step#2", "B", fence=2)
    assert second.id != row.id
    with db.session() as session:
        saved = list(session.scalars(select(DatasetWriteReceipt.result)))
        assert len(saved) == 2
        assert all(set(result) == {"row_id", "revision", "inserted"} for result in saved)


def test_delete_receipt_miss_does_not_stick_and_upsert_stays_serialized(client, db, writes):
    repo, dataset, base = writes
    call(client, "PUT", f"{base}/access/grants/receipts-flow", body={"permission": "write", "allow_delete": True})
    write(repo, dataset, "seed", "A")
    missing = WorkflowWrite(
        run_id="receipts-run", workflow_id="receipts-flow", operation_id="delete-missing",
        arguments={"operation": "delete_row", "row_id": "absent"}, fence=1,
    )
    with pytest.raises(AppError) as absent:
        repo.remove("owner", dataset, row_id="absent", match=None, workflow=missing)
    assert absent.value.code == "DATASET_ROW_NOT_FOUND"
    with db.session() as session:
        assert len(list(session.scalars(select(DatasetWriteReceipt)))) == 1
    deleted, replayed = repo.remove("owner", dataset, row_id=None, match=("ticket", "A"), workflow=WorkflowWrite(
        run_id="receipts-run", workflow_id="receipts-flow", operation_id="delete-a",
        arguments={"operation": "delete_row", "key": "ticket", "value": "A"}, fence=1,
    ))
    assert replayed is False
    again, replayed = repo.remove("owner", dataset, row_id=None, match=("ticket", "A"), workflow=WorkflowWrite(
        run_id="receipts-run", workflow_id="receipts-flow", operation_id="delete-a",
        arguments={"operation": "delete_row", "key": "ticket", "value": "A"}, fence=1,
    ))
    assert replayed is True and again == deleted
    with pytest.raises(AppError) as conflict:
        repo.remove("owner", dataset, row_id="other", match=None, workflow=WorkflowWrite(
            run_id="receipts-run", workflow_id="receipts-flow", operation_id="delete-a",
            arguments={"operation": "delete_row", "row_id": "other"}, fence=1,
        ))
    assert conflict.value.code == "DATASET_RECEIPT_CONFLICT"

    write(repo, dataset, "seed-b", "B")

    def upsert():
        return repo.save("owner", dataset, lambda _: {"ticket": "B"}, match=("ticket", "B"), workflow=WorkflowWrite(
            run_id="receipts-run", workflow_id="receipts-flow", operation_id="upsert-b",
            arguments={"operation": "upsert", "values": {"ticket": "B"}}, fence=1,
        ))

    def remove():
        return repo.remove("owner", dataset, row_id=None, match=("ticket", "B"), workflow=WorkflowWrite(
            run_id="receipts-run", workflow_id="receipts-flow", operation_id="delete-b",
            arguments={"operation": "delete_row", "key": "ticket", "value": "B"}, fence=1,
        ))

    with ThreadPoolExecutor(max_workers=2) as workers:
        list(workers.map(lambda fn: fn(), (upsert, remove)))
    with db.session() as session:
        remaining = list(session.scalars(select(DatasetWriteReceipt.operation_id)))
    assert {"delete-b", "upsert-b"} <= set(remaining)


def test_failed_write_has_no_receipt_and_revocation_blocks_replay(client, db, writes):
    repo, dataset, base = writes
    write(repo, dataset, "step#1", "A")
    with pytest.raises(AppError) as duplicate:
        write(repo, dataset, "step#2", "A")
    assert duplicate.value.code == "DATASET_UNIQUE_CONFLICT"
    with db.session() as session:
        assert len(list(session.scalars(select(DatasetWriteReceipt)))) == 1
    assert write(repo, dataset, "step#2", "B")[1]
    call(client, "DELETE", f"{base}/access/grants/receipts-flow")
    with pytest.raises(AppError) as denied:
        write(repo, dataset, "step#1", "A")
    assert denied.value.code == "DATASET_GRANT_DENIED"


def test_deleted_row_replay_and_worker_retention(client, db, writes, monkeypatch):
    import asyncio
    from unittest.mock import Mock

    from app.services import dataset_rows
    from app.services.run_worker import RunWorker

    repo, dataset, base = writes
    service = dataset_rows.DatasetRowService(None, repo)
    row, _, _ = write(repo, dataset, "old", "A")
    write(repo, dataset, "recent", "B")
    call(client, "DELETE", f"{base}/rows/{row.id}?revision=1")
    replay, inserted, reused = write(repo, dataset, "old", "A")
    assert reused
    assert dataset_rows._write_result(replay, inserted, ["ticket"]) == {
        "row": {"id": row.id, "revision": 1}, "inserted": True,
    }
    assert repo.get(dataset.id, row.id) is None

    with db.session() as session:
        session.execute(update(DatasetWriteReceipt).values(created=100000))
        session.execute(update(DatasetWriteReceipt).where(DatasetWriteReceipt.operation_id == "old").values(created=1))
        session.commit()
    monkeypatch.setenv("STUDIO_DATASET_RECEIPT_DAYS", "1")
    monkeypatch.setattr(dataset_rows, "time", lambda: 100000)
    worker = RunWorker(Mock(), Mock())

    def sweep():
        assert service.expire_receipts() == 1
        worker._stop = True

    worker.expire_dataset_receipts = sweep
    asyncio.run(asyncio.wait_for(worker.maintain(), timeout=5))
    replacement, _, replayed = write(repo, dataset, "old", "A")
    assert not replayed and replacement.id != row.id
    assert write(repo, dataset, "recent", "B")[2]


def test_receipt_migration_minimizes_all_cells_and_supports_downgrade(db):
    previous = "0068_dataset_team_owner"
    upgrade(db, previous)
    with db.session() as session:
        session.add(User(id="legacy-owner", email="legacy@example.com", role="editor"))
        session.flush()
        session.add(Dataset(id="legacy", owner_id="legacy-owner", name="Legacy", name_key="legacy", revision=1, created=1, updated=1))
        session.flush()
        session.add_all(
            DatasetWriteReceipt(dataset_id="legacy", scope="legacy", operation_id=str(i), fingerprint="x",
                                result={"row": {"id": str(i), "revision": 2, "values": {"private": f"secret-{i}"},
                                                "created": 1, "updated": 1}, "inserted": False}, created=1)
            for i in range(205)
        )
        deleted = {"row_id": "gone", "deleted": True}
        session.add(DatasetWriteReceipt(dataset_id="legacy", scope="legacy", operation_id="delete", fingerprint="x",
                                       result=deleted, created=1))
        session.commit()

    def results():
        with db.session() as session:
            return dict(session.execute(select(DatasetWriteReceipt.operation_id, DatasetWriteReceipt.result)).all())

    expected = {str(i): {"row_id": str(i), "revision": 2, "inserted": False} for i in range(205)}
    expected["delete"] = deleted
    upgrade(db, "0069_dataset_receipt_retention")
    assert results() == expected
    cfg = Config()
    cfg.set_main_option("script_location", MIGRATIONS_DIR)
    with db.engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.downgrade(cfg, previous)
    legacy = results()
    assert legacy.pop("delete") == deleted
    assert all(result["row"]["values"] == {} for result in legacy.values())
    upgrade(db, "0069_dataset_receipt_retention")
    assert results() == expected
