"""Synthetic support tickets for the public demo's read-only Dataset grid."""

from datetime import date, timedelta
from time import time

from ..models.database import Database
from ..models.team import Team, TeamMember
from ..repositories import AuditRepository, TeamRepository, UserRepository, WorkflowRepository, WorkflowShareRepository
from ..repositories.dataset_rows import DatasetRowRepository
from ..repositories.datasets import DatasetRepository
from ..schemas.dataset import DatasetColumnIn, DatasetCreate
from .access import AccessService
from .audit_service import AuditService
from .dataset_rows import _normalize
from .dataset_service import DatasetService

TEAM_ID = "demo-datasets"
DATASET_ID = "demo-support-tickets"
ROW_COUNT = 125

TEAMS = ("Support", "Billing", "Infrastructure")
STATUSES = ("Open", "Pending", "Closed")
LABELS = ("Access", "Hardware", "Billing", "Urgent")
REQUESTS = (
    ("Printer jam", "Support", "Hardware"),
    ("VPN access", "Infrastructure", "Access"),
    ("Invoice copy", "Billing", "Billing"),
    ("New starter laptop", "Support", "Hardware"),
    ("Guest Wi-Fi", "Infrastructure", "Access"),
    ("Update billing details", "Billing", "Billing"),
    ("Workshop projector", "Support", "Hardware"),
    ("Shared drive access", "Infrastructure", "Access"),
)


def _definition() -> DatasetCreate:
    return DatasetCreate(
        name="Support tickets",
        description="Sample tickets for trying filters, grouping, summaries, and paging.",
        team_id=TEAM_ID,
        columns=[
            DatasetColumnIn(key="ticket_id", label="Ticket ID", kind="auto_number"),
            DatasetColumnIn(key="subject", label="Subject", kind="text", required=True),
            DatasetColumnIn(key="team", label="Team", kind="select", options=list(TEAMS)),
            DatasetColumnIn(key="status", label="Status", kind="select", options=list(STATUSES)),
            DatasetColumnIn(key="priority", label="Priority", kind="number"),
            DatasetColumnIn(key="due_date", label="Due date", kind="date"),
            DatasetColumnIn(key="labels", label="Labels", kind="multi_select", options=list(LABELS)),
            DatasetColumnIn(key="reference", label="Reference", kind="url"),
            DatasetColumnIn(key="notes", label="Notes", kind="long_text"),
        ],
    )


def _ticket(index: int) -> dict:
    subject, team, label = REQUESTS[(index - 1) % len(REQUESTS)]
    priority = 1 + (index - 1) % 5
    return {
        "subject": f"{subject} · {index:03d}",
        "team": team,
        "status": STATUSES[(index - 1) % len(STATUSES)],
        "priority": priority,
        "due_date": (date(2026, 11, 1) + timedelta(days=(index - 1) % 31)).isoformat(),
        "labels": [label, "Urgent"] if priority == 5 else [label],
        "reference": f"https://example.org/support/tickets/{index}",
        "notes": (
            f"Fictional ticket about {subject.lower()}. The {team} team will review the request, "
            "check for related reports, and record the next action here."
        ) if index % 7 else None,
    }


def seed(db: Database, owner: str) -> None:
    teams = TeamRepository(db)
    now = time()
    if teams.get(TEAM_ID) is None:
        teams.save(Team(id=TEAM_ID, name="Superstep demo datasets", created=now, created_by=owner))
    teams.add_member(TeamMember(team_id=TEAM_ID, user_id=owner, added=now))
    repo = DatasetRepository(db)
    if repo.get(owner, DATASET_ID) is not None:
        return

    users = UserRepository(db)
    access = AccessService(users, WorkflowRepository(db), WorkflowShareRepository(db), teams)
    audit = AuditService(AuditRepository(db), users)
    dataset = DatasetService(repo, access, audit).prepare_create(owner, **_definition().model_dump())
    dataset.id = DATASET_ID
    records = []
    for index in range(1, ROW_COUNT + 1):
        ticket = _ticket(index)
        records.append({column.key: _normalize(column, ticket[column.key])
                        for column in dataset.columns if column.kind != "auto_number"})
    DatasetRowRepository(repo).import_rows(owner, dataset, records, create=True)
    audit.record(owner, "dataset.create", "dataset", dataset.id, rows=len(records))


def share(db: Database, visitor_ids: list[str], now: float) -> None:
    teams = TeamRepository(db)
    if teams.get(TEAM_ID) is None:
        return
    for uid in visitor_ids:
        teams.add_member(TeamMember(team_id=TEAM_ID, user_id=uid, added=now))
