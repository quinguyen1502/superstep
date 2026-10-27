from . import agent_server, approvals, auth, chat, chat_sessions, code, users, credentials, hooks, imports, knowledge, mcp, meta, notifications, public_chat, runs, runs_ws, templates, triggers, workflow_tests, workflows

ROUTERS = [auth.router, meta.router, workflows.router, credentials.router, imports.router, runs.router, runs_ws.router, triggers.router, hooks.router,
           notifications.router, notifications.ws_router, approvals.router, knowledge.router, mcp.router, users.router, templates.router, code.router, workflow_tests.router, chat.router, chat_sessions.router, public_chat.router, public_chat.root_router, agent_server.router]
