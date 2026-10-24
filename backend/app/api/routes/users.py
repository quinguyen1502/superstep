"""User administration and workflow sharing (TASK-0014)."""
from fastapi import APIRouter, Depends, Query
from ...core import permissions as P
from ...schemas.rbac import MemberIn, LangSmithIn, PolicyIn, ShareIn, TeamIn, TeamShareIn, TransferIn, UserDelete, UserUpdate
from ..deps import audit_service, current_user, langsmith_service, ownership_service, policy_service, share_service, team_service, user_service, workflow_service

router = APIRouter(prefix="/api", tags=["rbac"])

@router.get("/roles")
def roles(user=Depends(current_user)): return P.matrix()

@router.get("/admin/users")
def list_users(user=Depends(current_user), svc=Depends(user_service)): return svc.list(user["id"])

@router.patch("/admin/users/{target}")
def update_user(target: str, body: UserUpdate, user=Depends(current_user), svc=Depends(user_service)):
    return svc.update(user["id"], target, body.role, body.active)

@router.get("/workflows/{wid}/shares")
def list_shares(wid: str, user=Depends(current_user), svc=Depends(share_service)): return svc.list(wid, user["id"])

@router.put("/workflows/{wid}/shares")
def put_share(wid: str, body: ShareIn, user=Depends(current_user), svc=Depends(share_service)): return svc.put(wid, user["id"], body.email, body.role)

@router.delete("/workflows/{wid}/shares/{target}")
def delete_share(wid: str, target: str, user=Depends(current_user), svc=Depends(share_service)): return svc.remove(wid, user["id"], target)


# ---- TASK-0029: teams, team shares, ownership transfer, account deletion, audit, policy ----


@router.delete("/admin/users/{target}")
def delete_user(target: str, body: UserDelete, user=Depends(current_user), svc=Depends(user_service)):
    return svc.delete(user["id"], target, body.mode, body.reassign_to)

@router.get("/admin/audit")
def audit(category: str | None = None, q: str | None = None, since: str | None = None, limit: int = Query(50, ge=1, le=200),
          offset: int = Query(0, ge=0), user=Depends(current_user), svc=Depends(audit_service)):
    return svc.list(user["id"], category, q, since, limit, offset)

@router.get("/admin/policy")
def get_policy(user=Depends(current_user), svc=Depends(policy_service)): return svc.get(user["id"])

@router.put("/admin/policy")
def put_policy(body: PolicyIn, user=Depends(current_user), svc=Depends(policy_service)): return svc.update(user["id"], body.org_resources_roles)

@router.get("/admin/langsmith")
def get_langsmith(user=Depends(current_user), svc=Depends(langsmith_service)): return svc.get(user["id"])

@router.put("/admin/langsmith")
def put_langsmith(body: LangSmithIn, user=Depends(current_user), svc=Depends(langsmith_service)): return svc.update(user["id"], body.evals)

@router.get("/teams")
def list_teams(user=Depends(current_user), svc=Depends(team_service)): return svc.list(user["id"])

@router.post("/teams")
def create_team(body: TeamIn, user=Depends(current_user), svc=Depends(team_service)): return svc.create(user["id"], body.name or "", body.description)

@router.patch("/teams/{tid}")
def update_team(tid: str, body: TeamIn, user=Depends(current_user), svc=Depends(team_service)): return svc.update(user["id"], tid, body.name, body.description)

@router.delete("/teams/{tid}")
def delete_team(tid: str, user=Depends(current_user), svc=Depends(team_service)): return svc.delete(user["id"], tid)

@router.post("/teams/{tid}/members")
def add_member(tid: str, body: MemberIn, user=Depends(current_user), svc=Depends(team_service)): return svc.add_member(user["id"], tid, body.email)

@router.delete("/teams/{tid}/members/{member}")
def remove_member(tid: str, member: str, user=Depends(current_user), svc=Depends(team_service)): return svc.remove_member(user["id"], tid, member)

@router.put("/workflows/{wid}/team-shares")
def put_team_share(wid: str, body: TeamShareIn, user=Depends(current_user), svc=Depends(share_service)):
    return svc.put_team(wid, user["id"], body.team_id, body.role)

@router.delete("/workflows/{wid}/team-shares/{tid}")
def delete_team_share(wid: str, tid: str, user=Depends(current_user), svc=Depends(share_service)): return svc.remove_team(wid, user["id"], tid)

@router.get("/workflows/{wid}/transfer")
def transfer_preview(wid: str, email: str, user=Depends(current_user), svc=Depends(ownership_service)): return svc.preview(wid, user["id"], email)

@router.post("/workflows/{wid}/transfer")
def transfer(wid: str, body: TransferIn, user=Depends(current_user), svc=Depends(ownership_service)):
    return svc.transfer(wid, user["id"], body.email, body.rebind, body.keep_access)

@router.get("/workflows/{wid}/dependents")
def dependents(wid: str, user=Depends(current_user), svc=Depends(workflow_service)):
    svc.owned(wid, user["id"]); return {"dependents": svc.dependents(wid, user["id"])}
