"""Writes the public-only OpenAPI spec (the workflow-trigger API and the Chat API v1) and the AsyncAPI document of the
chat socket v1 (docs/asyncapi/chat-v1.yaml, TASK-0216) from the backend app.

  python scripts/gen_public_openapi.py           write the files below
  python scripts/gen_public_openapi.py --check   exit 1 when a committed file differs from the app

Targets: docs/api/openapi.public.json (the source for the SDKs) and a copy in the handbook, where the API reference page
renders it. Run with the backend's Python (it imports `app`); backend/tests/test_public_openapi.py runs the check too.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "docs/api/openapi.public.json", ROOT / "handbook/docs/en/reference/openapi.public.json"]


def render() -> str:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.api.openapi_public import public_openapi
    return json.dumps(public_openapi(), indent=2, ensure_ascii=False) + "\n"


ASYNCAPI = ROOT / "docs/asyncapi/chat-v1.yaml"


def render_asyncapi() -> str:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.api.asyncapi_public import render as asyncapi
    return asyncapi()


def main(check: bool) -> int:
    text, stale = render(), []
    for path, content in [(p, text) for p in TARGETS] + [(ASYNCAPI, render_asyncapi())]:
        if check:
            if not path.exists() or path.read_text() != content: stale.append(path.relative_to(ROOT))
        else:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
    for p in stale: print(f"{p} is out of date: run python scripts/gen_public_openapi.py", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
