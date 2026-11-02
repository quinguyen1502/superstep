"""Seed synthetic chat integration fixtures on sdk_integration.sh's temporary backend only."""
import json
import os
import sys
import httpx

base, destination = sys.argv[1:]
client = httpx.Client(base_url=base, timeout=30)


def api(method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    payload = response.json()
    if not payload["success"]:
        raise RuntimeError(f"SDK fixture setup failed: {payload['error']['code']}")
    return payload["data"]


owner = api("POST", "/api/auth/login", json={"email": "admin@example.com", "password": "admin123"})["token"]
client.headers["Authorization"] = f"Bearer {owner}"
workflow_token = api("POST", "/api/workflows/example/tokens", json={"name": "sdk-it"})["token"]


def node(identifier, kind, **data):
    return {"id": identifier, "type": kind, "position": {"x": 0, "y": 0}, "data": {"label": identifier, **data}}


def seed(slug, human=False):
    nodes = [node("s", "start")]
    if human:
        nodes.append(node("ask", "human", prompt="Confirm {{state.message}}?", output_field="answer"))
    nodes += [node("bot", "llm", prompt="Answer: {{state.messages}} {{state.answer}}", output_field="reply"), node("e", "end")]
    workflow = {"name": slug, "state": [{"name": "message", "type": "string"}, {"name": "messages", "type": "list"},
        {"name": "reply", "type": "string"}, {"name": "answer", "type": "object"}, {"name": "files", "type": "list"}, {"name": "chat", "type": "object"}],
        "nodes": nodes, "edges": [{"id": str(i), "source": left["id"], "target": right["id"]} for i, (left, right) in enumerate(zip(nodes, nodes[1:]))]}
    wid = api("POST", "/api/workflows", json=workflow)["id"]
    api("PUT", f"/api/workflows/{wid}/chat", json={"enabled": True, "slug": slug, "access": ["app", "anonymous"],
        "attachments": {"enabled": True, "field": "files"}})
    key = api("POST", f"/api/workflows/{wid}/chat/app-keys", json={"label": "SDK integration"})
    return {"slug": slug, "workflowId": wid, "keyId": key["key_id"], "secret": key["secret"]}


config = {"owner": owner, "chat": seed("sdk-chat-it"), "human": seed("sdk-human-it", human=True)}
with open(destination, "w", encoding="utf8") as out:
    os.chmod(destination, 0o600)
    json.dump(config, out)
# Captured by the parent shell; never printed to CI logs.
print("example", workflow_token)
