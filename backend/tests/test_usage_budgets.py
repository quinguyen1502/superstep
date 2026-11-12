"""Monthly budgets through the admin API and concurrent warning evaluation."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import time

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import usage_budget_service
from app.main import app
from app.models import Notification, Team, TeamMember
from app.models.run_usage import RunUsage
from app.models.usage_budget import UsageBudgetWarning
from app.services.usage_budgets import month_window


def test_monthly_budgets(monkeypatch):
    monkeypatch.setenv("STUDIO_TIMEZONE", "Asia/Ho_Chi_Minh")
    boundary = datetime(2026, 10, 31, 18, tzinfo=timezone.utc).timestamp()
    assert month_window(boundary)[0] == "2026-11"

    with TestClient(app) as client:
        def auth(path, email, password):
            token = client.post(path, json={"email": email, "password": password}).json()["data"]["token"]
            return {"Authorization": f"Bearer {token}"}

        admin = auth("/api/auth/login", "admin@example.com", "admin123")
        email = "budget-regression@example.com"
        user = auth("/api/auth/register", email, "secret12")
        path = "/api/admin/usage/budgets"
        assert client.get(path, headers=user).status_code == 403
        targets = client.get(path, headers=admin).json()["data"]["targets"]
        uid = next(target["id"] for target in targets if target["name"] == email)
        svc = usage_budget_service()
        now = time.time()
        _, since, _, _ = month_window(now)
        with svc.repo.db.session() as session:
            session.add(Team(id="budget-team", name="Budget team", created=now, created_by=uid))
            session.flush()
            session.add(TeamMember(team_id="budget-team", user_id=uid, added=now))
            session.commit()

        def create(scope, target):
            response = client.post(path, headers=admin, json={"scope": scope, "target_id": target, "amount_usd": "10"})
            assert response.status_code == 201, response.text
            return response.json()["data"]["id"]

        user_budget = create("user", uid)
        team_budget = create("team", "budget-team")
        assert client.post(path, headers=admin, json={"scope": "user", "target_id": uid, "amount_usd": "10"}).status_code == 409

        def write_usage(ident, cost, at):
            with svc.repo.db.session() as session:
                session.add(RunUsage(id=ident, run_id=ident, workflow_id="workflow", owner=uid, node_id="node",
                                     kind="llm", model="m", provider="p", cost_usd=cost, created=at))
                session.commit()

        write_usage("budget-run-priced", 8.0, now)
        write_usage("budget-run-unpriced", None, now)
        write_usage("budget-run-old", 99.0, since - 1)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: svc.check_owner(uid, now), range(8)))
        with svc.repo.db.session() as session:
            query = select(UsageBudgetWarning.threshold).where(UsageBudgetWarning.budget_id.in_((user_budget, team_budget)))
            assert sorted(session.scalars(query)) == [80, 80]
            notices = session.scalars(select(Notification).where(Notification.user_id == uid))
            assert sorted(json.loads(notice.params)["threshold"] for notice in notices) == [80, 80]

        write_usage("budget-run-threshold", 2.0, now)
        svc.check_owner(uid, now)
        svc.check_owner(uid, now)
        rows = client.get(path, headers=admin).json()["data"]["budgets"]
        tracked = {r["id"]: (r["spent_usd"], r["unpriced_rows"]) for r in rows if r["id"] in (user_budget, team_budget)}
        assert tracked == {user_budget: (10.0, 1), team_budget: (10.0, 1)}
        with svc.repo.db.session() as session:
            assert sorted(session.scalars(query)) == [80, 80, 100, 100]
        assert client.patch(f"{path}/{user_budget}", headers=admin, json={"amount_usd": 12}).status_code == 200
        assert client.delete(f"{path}/{user_budget}", headers=admin).status_code == 200
        assert client.delete(f"{path}/{user_budget}", headers=admin).status_code == 404
        assert client.delete(f"{path}/{team_budget}", headers=admin).status_code == 200
