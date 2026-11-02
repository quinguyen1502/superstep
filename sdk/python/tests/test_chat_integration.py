"""Real HTTP and websockets sync/async; ephemeral backend/key configuration comes from sdk_integration.sh."""
import inspect
import json
import os
from pathlib import Path

import httpx
import pytest

from superstep import Client, AsyncClient, NotFoundError, mint_chat_token

BASE = os.environ.get("SUPERSTEP_IT_BASE_URL")
FILE = os.environ.get("SUPERSTEP_IT_CHAT_CONFIG")
CONFIG = json.loads(Path(FILE).read_text()) if FILE else None
pytestmark = pytest.mark.skipif(not BASE or CONFIG is None, reason="run scripts/sdk_integration.sh for ephemeral chat configuration")


async def maybe(value): return await value if inspect.isawaitable(value) else value


async def drain(stream):
    if hasattr(stream, "__aiter__"):
        async with stream:
            async for _ in stream: pass
    else:
        with stream:
            for _ in stream: pass
    return stream.result


def token(key, user):
    return mint_chat_token(key["keyId"], key["secret"], key["slug"], user, "Python SDK user", meta={"locale": "vi"})


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
async def test_live_chat_session_stream_files_ratings_and_isolation(asynchronous):
    parent = (AsyncClient if asynchronous else Client)(base_url=BASE)
    key = CONFIG["chat"]
    try:
        chat = parent.chat(key["slug"], token=lambda: token(key, f"python-{asynchronous}"))
        assert (await maybe(chat.info()))["slug"] == key["slug"]
        session = await maybe(chat.start()); sid = session["id"]
        file = await maybe(chat.attachments.upload(sid, b"hello file", filename="sdk.txt", content_type="text/plain"))
        assert (await maybe(chat.attachments.download(sid, file["id"]))).content == b"hello file"
        assert await maybe(chat.attachments.delete(sid, file["id"])) == {"ok": True}
        result = await drain(chat.send(sid, "Hello from Python", recovery_interval=0.025))
        assert result.status == "ok" and result.turn_id and "Hello from Python" in result.text and not result.recovered
        assert len((await maybe(chat.get(sid)))["turns"]) == 2
        assert sid in [item["id"] for item in (await maybe(chat.list()))["sessions"]]
        assert (await maybe(chat.turns(sid, after=result.turns[0]["id"])))["turns"][0]["id"] == result.turn_id
        assert (await maybe(chat.ratings.put(sid, result.turn_id, "down", comment="Integration test")))["value"] == "down"
        assert await maybe(chat.ratings.delete(sid, result.turn_id)) == {"ok": True}
        other = parent.chat(key["slug"], token=token(key, f"python-other-{asynchronous}"))
        with pytest.raises(NotFoundError): await maybe(other.get(sid))
        assert (await maybe(other.list()))["sessions"] == []
    finally: await maybe(parent.aclose() if asynchronous else parent.close())


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize("answer", ["yes", {"approved": True, "note": "Confirmed"}], ids=["text", "form"])
async def test_live_human_answer(asynchronous, answer):
    parent = (AsyncClient if asynchronous else Client)(base_url=BASE)
    key = CONFIG["human"]
    try:
        chat = parent.chat(key["slug"], token=lambda: token(key, f"python-human-{asynchronous}-{type(answer).__name__}"))
        sid = (await maybe(chat.start()))["id"]
        waiting = await drain(chat.send(sid, "approval", recovery_interval=0.025))
        assert waiting.status == "waiting" and waiting.question["node"] == "ask"
        result = await drain(chat.answer(sid, answer, node="ask", recovery_interval=0.025))
        assert result.status == "ok" and result.turn_id != waiting.turn_id
        turns = (await maybe(chat.get(sid)))["turns"]
        assert any(turn["role"] == "user" and (answer if isinstance(answer, str) else "approved: true") in turn["text"] for turn in turns)
        if isinstance(answer, dict): assert "approved" in result.text
    finally: await maybe(parent.aclose() if asynchronous else parent.close())
