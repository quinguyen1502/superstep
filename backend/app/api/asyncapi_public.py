"""The AsyncAPI 3.0 document of the chat socket protocol v1 (TASK-0216, DEC-0078), built from the JSON Schema files in
`api/schemas/chat_ws_v1/` (the contract tests validate frames against the same files).

Served at GET /asyncapi.public.yaml and committed as docs/asyncapi/chat-v1.yaml by scripts/gen_public_openapi.py.
"""
import json, pathlib
import yaml
from fastapi import FastAPI
from fastapi.responses import Response

SCHEMAS = pathlib.Path(__file__).resolve().parent / "schemas/chat_ws_v1"
DESCRIPTION = """The published chat's socket, version 1. Open `/ws/public/v1/chat/{slug}`, wait for `ready`, optionally
send `auth`, then send one `message` or `answer`. The run streams as typed frames, each with `v` (1) and `seq`, and ends
with `done` (after `turn` when the answer is saved in time) or `error`; then the server closes the socket. One message
per connection. `cancel` stops the run. Clients must ignore fields and frame types they do not know: v1 only grows.
Error codes are those of the HTTP API (docs/api-errors.md); a frame that is not v1 is `CHAT_FRAME_INVALID`.
"""


def load(name: str) -> dict: return json.loads((SCHEMAS / f"{name}.json").read_text())


def messages(schema: dict, prefix: str) -> dict:
    defs = {k: v for k, v in schema["$defs"].items() if k != "base"}
    return {f"{prefix}_{k}": {"name": k, "title": k, "payload": {"$ref": f"#/components/schemas/{prefix}_{k}"}} for k in defs}


def rebase(node, prefix: str):
    """Moves the files' `#/$defs/x` references to `#/components/schemas/<prefix>_x`."""
    if isinstance(node, dict):
        return {k: (f"#/components/schemas/{prefix}_{v.rsplit('/', 1)[1]}" if k == "$ref" and isinstance(v, str) and v.startswith("#/$defs/")
                    else rebase(v, prefix)) for k, v in node.items()}
    if isinstance(node, list): return [rebase(x, prefix) for x in node]
    return node


def asyncapi() -> dict:
    client, server = load("client"), load("server")
    schemas = {**{f"client_{k}": rebase(v, "client") for k, v in client["$defs"].items()},
               **{f"server_{k}": rebase(v, "server") for k, v in server["$defs"].items()}}
    cm, sm = messages(client, "client"), messages(server, "server")
    return {
        "asyncapi": "3.0.0",
        "info": {"title": "Superstep chat socket", "version": "1.0.0", "description": " ".join(DESCRIPTION.split())},
        "channels": {"chat": {"address": "/ws/public/v1/chat/{slug}", "parameters": {"slug": {"description": "The chat's page address."}},
                              "messages": {**{k: {"$ref": f"#/components/messages/{k}"} for k in cm}, **{k: {"$ref": f"#/components/messages/{k}"} for k in sm}}}},
        "operations": {
            "sendFrame": {"action": "send", "channel": {"$ref": "#/channels/chat"}, "summary": "A client frame.",
                          "messages": [{"$ref": f"#/channels/chat/messages/{k}"} for k in cm]},
            "receiveFrame": {"action": "receive", "channel": {"$ref": "#/channels/chat"}, "summary": "A server frame.",
                             "messages": [{"$ref": f"#/channels/chat/messages/{k}"} for k in sm]}},
        "components": {"schemas": schemas, "messages": {**cm, **sm}},
    }


def render() -> str: return yaml.safe_dump(asyncapi(), sort_keys=False, allow_unicode=True, width=120)


def install_asyncapi(app: FastAPI) -> None:
    text = render()

    @app.get("/asyncapi.public.yaml", include_in_schema=False)
    def asyncapi_spec(): return Response(text, media_type="application/yaml")
