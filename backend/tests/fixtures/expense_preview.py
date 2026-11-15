"""Isolated browser-test app. Replaces paid models/Google HTTP only; never a production entry point."""
import json, os, time
from urllib.parse import unquote

if os.environ.get("STUDIO_E2E_EXPENSE_FIXTURE") != "1":
    raise RuntimeError("This fixture requires the explicit isolated E2E flag")

import httpx
from app.main import app
from app.engine import nodes
from app.engine.providers import ProviderError
from app.services.managed_tools import sheets

ROWS = {}


def model(prompt, name, credential, on_usage=None, on_token=None, **kwargs):
    if credential and credential.get("provider") == "openrouter":
        raise ProviderError("PROVIDER_UNREACHABLE", "openrouter")
    return json.dumps({"is_expense": True, "amount": 50000, "description": "Lunch", "category": "Food", "expense_date": "2026-10-31"}, ensure_ascii=False)


def google_request(method, url, **kwargs):
    if url == sheets.TOKEN_URL:
        assert kwargs["data"]["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
        return httpx.Response(200, json={"access_token": "fixture-only"})
    prefix = sheets.API + "/"
    assert url.startswith(prefix)
    spreadsheet = unquote(url[len(prefix):].split("/", 1)[0])
    rows = ROWS.setdefault(spreadsheet, [])
    if method == "GET":
        return httpx.Response(200, json={"values": [[row["values"][-1]] for row in rows]})
    assert method == "POST" and url.endswith(":append") and kwargs["params"]["valueInputOption"] == "RAW"
    values = kwargs["json"]["values"][0]
    rows.append({"values": values, "at": time.time()})
    column = chr(ord("A") + len(values) - 1)
    return httpx.Response(200, json={"updates": {"updatedRows": 1, "updatedRange": f"Expenses!A{len(rows)}:{column}{len(rows)}"}})


nodes.call_llm = model
sheets.request = google_request


@app.get("/api/_expense-fixture")
def recorded_rows():
    return {"rows": ROWS}
