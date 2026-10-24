from typing import Optional
from sqlalchemy import Boolean, Float, Index, Integer, Text, false, text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class WorkflowTest(Base):
    """A test case of a workflow (TASK-0067): an input, the answers for its Human nodes and the checks a run must pass."""
    __tablename__ = "workflow_tests"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(Text, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    input: Mapped[str] = mapped_column(Text, nullable=False)    # JSON object, like a run's input
    answers: Mapped[str] = mapped_column(Text, nullable=False)  # JSON {human node id: [answer, ...]}, used in order
    checks: Mapped[str] = mapped_column(Text, nullable=False)   # JSON list, engine.checks
    position: Mapped[int] = mapped_column(Integer, default=0)
    author: Mapped[Optional[str]] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float, nullable=False)
    updated: Mapped[float] = mapped_column(Float, nullable=False)


class WorkflowTestSuite(Base):
    """One "Run all" (or run one) of a workflow's test cases. At most one runs per workflow at a time."""
    __tablename__ = "workflow_test_suites"
    __table_args__ = (Index("uq_workflow_test_suites_running", "workflow_id", unique=True,
                            sqlite_where=text("status = 'running'"), postgresql_where=text("status = 'running'")),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(Text, index=True)
    version: Mapped[Optional[int]] = mapped_column(Integer)  # the saved version when the suite started
    owner: Mapped[str] = mapped_column(Text, nullable=False)  # who ran it; the test runs are theirs
    status: Mapped[str] = mapped_column(Text, nullable=False)  # running | done | cancelled
    mock: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())  # offline mock model for every LLM node
    total: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    started: Mapped[float] = mapped_column(Float, nullable=False)
    ended: Mapped[Optional[float]] = mapped_column(Float)
    langsmith_url: Mapped[Optional[str]] = mapped_column(Text)  # the LangSmith experiment of this suite run, once sent


class WorkflowTestResult(Base):
    """One test case in a suite: a copy of the case as it ran, its test run and the result of each check."""
    __tablename__ = "workflow_test_results"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    suite_id: Mapped[str] = mapped_column(Text, index=True)
    test_id: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    case: Mapped[str] = mapped_column(Text, nullable=False)  # JSON {input, answers, checks} as it ran
    position: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(Text, nullable=False)  # queued | running | passed | failed | cancelled
    run_id: Mapped[Optional[str]] = mapped_column(Text, index=True)
    version: Mapped[Optional[int]] = mapped_column(Integer)  # the version the test run ran
    checks: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of engine.checks results
    reason: Mapped[Optional[str]] = mapped_column(Text)  # why the case failed without a check: no_answer | run_failed | ...
    detail: Mapped[Optional[str]] = mapped_column(Text)  # e.g. the Human node with no answer left
    ended: Mapped[Optional[float]] = mapped_column(Float)
