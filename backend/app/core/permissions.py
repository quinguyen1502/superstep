"""Roles and permissions. Fixed in code: the single source for the API, the admin UI matrix and tests.

Global role (users.role): what a user may do in the studio.
Workflow access: owner, or a share (viewer | editor); admins act as owner on every workflow."""

ROLES = ("admin", "editor", "viewer")
DEFAULT_ROLE = "editor"

# global permissions
USERS_MANAGE = "users.manage"          # list users, change roles, (de)activate accounts
ORG_MANAGE = "org.manage"              # org-wide approval channels and MCP servers, stdio MCP servers
WORKFLOWS_ALL = "workflows.all"        # owner-level access to every workflow
WORKFLOWS_CREATE = "workflows.create"  # create, import and duplicate workflows
RESOURCES_MANAGE = "resources.manage"  # own credentials, knowledge bases, personal MCP servers, API tokens
CODE_WRITE = "code.write"              # add a Tool node in Code mode or change its source

PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset({USERS_MANAGE, ORG_MANAGE, WORKFLOWS_ALL, WORKFLOWS_CREATE, RESOURCES_MANAGE, CODE_WRITE}),
    "editor": frozenset({WORKFLOWS_CREATE, RESOURCES_MANAGE}),
    "viewer": frozenset(),  # opens and runs workflows shared with them; creates nothing
}

# workflow actions
VIEW, RUN, EDIT, DELETE, SHARE, TRANSFER = "view", "run", "edit", "delete", "share", "transfer"
SHARE_ROLES = ("viewer", "editor")
WORKFLOW_ACTIONS: dict[str, frozenset[str]] = {
    "owner": frozenset({VIEW, RUN, EDIT, DELETE, SHARE, TRANSFER}),
    "editor": frozenset({VIEW, RUN, EDIT}),
    "viewer": frozenset({VIEW, RUN}),
}


def best_share(roles) -> str | None:
    """The strongest share role among direct and team shares (editor > viewer)."""
    rs = [r for r in roles if r in SHARE_ROLES]
    return "editor" if "editor" in rs else ("viewer" if rs else None)


# org-wide approval channels and MCP servers at run time (admin policy, ); admins always may
ORG_RESOURCE_DEFAULT = ("admin", "editor")


def _lang_prefix(data: dict) -> str:
    lang = str(data.get("language") or "python")
    return "" if lang == "python" else f"[{lang}]\n"


def code_sources(graph: dict | None) -> dict[str, str]:
    """Node id -> language and source of every Tool node in Code mode (; the language , so
    switching a node to another language is writing code too). Python nodes keep the bare source (no language key)."""
    nodes = (graph or {}).get("nodes") if isinstance(graph, dict) else None
    return {str(n.get("id")): _lang_prefix(n.get("data") or {}) + str((n.get("data") or {}).get("code") or "") for n in (nodes or [])
            if isinstance(n, dict) and n.get("type") == "tool" and (n.get("data") or {}).get("mode") == "code"}


def code_written(before: dict | None, after: dict | None) -> bool:
    """True when `after` adds a Code node or changes one's source. Moving, renaming or deleting one is not writing code."""
    old = code_sources(before)
    return any(old.get(nid) != src for nid, src in code_sources(after).items())


def can(role: str | None, permission: str) -> bool:
    return permission in PERMISSIONS.get(role or "", frozenset())


def workflow_role(user_role: str | None, is_owner: bool, share_role: str | None) -> str | None:
    """Effective access to one workflow: owner | editor | viewer | None. A global viewer never edits (share capped)."""
    if is_owner or can(user_role, WORKFLOWS_ALL): return "owner"
    if share_role not in SHARE_ROLES: return None
    return "viewer" if user_role == "viewer" else share_role


def matrix() -> dict:
    """For the admin UI: every role with its permissions, and the workflow access levels."""
    perms = [USERS_MANAGE, ORG_MANAGE, WORKFLOWS_ALL, WORKFLOWS_CREATE, RESOURCES_MANAGE, CODE_WRITE]
    return {"roles": [{"role": r, "permissions": sorted(PERMISSIONS[r])} for r in ROLES], "permissions": perms,
            "workflow_access": [{"access": a, "actions": sorted(WORKFLOW_ACTIONS[a], key=[VIEW, RUN, EDIT, DELETE, SHARE, TRANSFER].index)} for a in WORKFLOW_ACTIONS]}
