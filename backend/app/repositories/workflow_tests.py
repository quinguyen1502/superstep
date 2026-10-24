from typing import Optional
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from ..models import User, WorkflowTest, WorkflowTestResult, WorkflowTestSuite
from ..models.database import Database


class WorkflowTestRepository:
    """Test cases, suite runs and results of workflow tests (TASK-0067). Status changes are compare-and-set."""
    def __init__(self, db: Database): self.db = db

    # ---- test cases ----
    def add(self, t: WorkflowTest) -> WorkflowTest:
        with self.db.session() as s: s.add(t); s.commit(); s.refresh(t); return t

    def get(self, tid: str) -> Optional[WorkflowTest]:
        with self.db.session() as s: return s.get(WorkflowTest, tid)

    def list_for_workflow(self, wid: str) -> list[WorkflowTest]:
        with self.db.session() as s:
            return list(s.scalars(select(WorkflowTest).where(WorkflowTest.workflow_id == wid).order_by(WorkflowTest.position, WorkflowTest.created)))

    def count_for_workflow(self, wid: str) -> int:
        with self.db.session() as s: return s.scalar(select(func.count()).select_from(WorkflowTest).where(WorkflowTest.workflow_id == wid)) or 0

    def set_fields(self, tid: str, **values) -> None:
        with self.db.session() as s: s.execute(update(WorkflowTest).where(WorkflowTest.id == tid).values(**values)); s.commit()

    def delete(self, tid: str) -> None:
        with self.db.session() as s: s.execute(delete(WorkflowTest).where(WorkflowTest.id == tid)); s.commit()

    def delete_for_workflow(self, wid: str) -> None:
        with self.db.session() as s:
            suites = select(WorkflowTestSuite.id).where(WorkflowTestSuite.workflow_id == wid)
            s.execute(delete(WorkflowTestResult).where(WorkflowTestResult.suite_id.in_(suites)))
            s.execute(delete(WorkflowTestSuite).where(WorkflowTestSuite.workflow_id == wid))
            s.execute(delete(WorkflowTest).where(WorkflowTest.workflow_id == wid)); s.commit()

    # ---- suite runs ----
    def start_suite(self, suite: WorkflowTestSuite, results: list[WorkflowTestResult]) -> bool:
        """Insert a running suite with its queued results. False when the workflow already has a running suite."""
        with self.db.session() as s:
            try: s.add(suite); s.add_all(results); s.commit(); return True
            except IntegrityError: s.rollback(); return False

    def suite(self, sid: str) -> Optional[WorkflowTestSuite]:
        with self.db.session() as s: return s.get(WorkflowTestSuite, sid)

    def suites(self, wid: str, limit: int = 20) -> list[tuple[WorkflowTestSuite, Optional[str]]]:
        """Newest first, with the email of who ran each one (None when that user was deleted)."""
        with self.db.session() as s:
            q = (select(WorkflowTestSuite, User.email).outerjoin(User, User.id == WorkflowTestSuite.owner)
                 .where(WorkflowTestSuite.workflow_id == wid).order_by(WorkflowTestSuite.started.desc()).limit(limit))
            return [(t, e) for t, e in s.execute(q)]

    def baseline(self, wid: str, version: int) -> Optional[WorkflowTestSuite]:
        """The latest finished suite run on a version older than `version` (TASK-0068)."""
        with self.db.session() as s:
            return s.scalars(select(WorkflowTestSuite).where(WorkflowTestSuite.workflow_id == wid, WorkflowTestSuite.status == "done",
                                                             WorkflowTestSuite.version < version).order_by(WorkflowTestSuite.started.desc()).limit(1)).first()

    def end_suite(self, sid: str, status: str, passed: int, failed: int, now: float) -> bool:
        with self.db.session() as s:
            n = s.execute(update(WorkflowTestSuite).where(WorkflowTestSuite.id == sid, WorkflowTestSuite.status == "running")
                          .values(status=status, passed=passed, failed=failed, ended=now)).rowcount
            s.commit(); return n == 1

    def set_suite(self, sid: str, **values) -> None:
        with self.db.session() as s: s.execute(update(WorkflowTestSuite).where(WorkflowTestSuite.id == sid).values(**values)); s.commit()

    # ---- results ----
    def results(self, sid: str) -> list[WorkflowTestResult]:
        with self.db.session() as s:
            return list(s.scalars(select(WorkflowTestResult).where(WorkflowTestResult.suite_id == sid).order_by(WorkflowTestResult.position)))

    def result_for_run(self, rid: str) -> Optional[WorkflowTestResult]:
        with self.db.session() as s: return s.scalars(select(WorkflowTestResult).where(WorkflowTestResult.run_id == rid)).first()

    def latest_results(self, test_ids: list[str]) -> dict[str, WorkflowTestResult]:
        """The most recent finished result of each test case."""
        if not test_ids: return {}
        with self.db.session() as s:
            rows = s.execute(select(WorkflowTestResult, WorkflowTestSuite.started).join(WorkflowTestSuite, WorkflowTestSuite.id == WorkflowTestResult.suite_id)
                             .where(WorkflowTestResult.test_id.in_(test_ids), WorkflowTestResult.status.in_(("passed", "failed")))
                             .order_by(WorkflowTestSuite.started.desc())).all()
        out: dict[str, WorkflowTestResult] = {}
        for r, _ in rows: out.setdefault(r.test_id, r)
        return out

    def claim_result(self, res_id: str, run_id: str) -> bool:
        """queued -> running with its test run id: one worker starts each case."""
        with self.db.session() as s:
            n = s.execute(update(WorkflowTestResult).where(WorkflowTestResult.id == res_id, WorkflowTestResult.status == "queued")
                          .values(status="running", run_id=run_id)).rowcount
            s.commit(); return n == 1

    def finish_result(self, res_id: str, status: str, now: float, **values) -> bool:
        """running (or queued, on cancel) -> a final status, once."""
        with self.db.session() as s:
            n = s.execute(update(WorkflowTestResult).where(WorkflowTestResult.id == res_id, WorkflowTestResult.status.in_(("queued", "running")))
                          .values(status=status, ended=now, **values)).rowcount
            s.commit(); return n == 1
