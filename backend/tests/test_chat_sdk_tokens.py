"""Shared synthetic vectors: the TypeScript server helper signs what our real verifier accepts."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from app.core import crypto
from app.core.errors import AppError
from app.services.chat_token_verifier import Hs256ChatTokenVerifier

ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads((ROOT / "sdk/fixtures/chat-token-vectors.json").read_text())["vectors"]


@pytest.mark.parametrize("vector", VECTORS, ids=["ascii", "unicode"])
def test_sdk_signed_token_verifies_and_preserves_identity(vector):
    options = vector["options"]
    key = SimpleNamespace(id=options["keyId"], trigger_id="sdk-trigger", secret_enc=crypto.encrypt(options["secret"]), origins="[]", revoked_at=None)
    used = []
    keys = SimpleNamespace(get=lambda kid: key if kid == key.id else None, used=lambda kid, now: used.append((kid, now)) or True)
    verifier = Hs256ChatTokenVerifier(keys, clock=lambda: vector["issuedAt"])
    user = verifier.verify(vector["token"], options["slug"], "sdk-trigger", None)
    assert (user.id, user.name, user.meta, user.app_key_id) == (options["userId"], options.get("name", ""), options.get("meta", {}), key.id)
    assert used == [(key.id, vector["issuedAt"])]
    for slug, trigger in [("other-chat", "sdk-trigger"), (options["slug"], "other-trigger")]:
        with pytest.raises(AppError) as error: verifier.verify(vector["token"], slug, trigger, None)
        assert error.value.code == "CHAT_TOKEN_INVALID"
    verifier.clock = lambda: vector["issuedAt"] + options.get("ttl", 600) + 60
    with pytest.raises(AppError) as error: verifier.verify(vector["token"], options["slug"], "sdk-trigger", None)
    assert error.value.code == "CHAT_TOKEN_EXPIRED"


def test_sdk_recorded_frames_match_the_published_schema():
    schema = json.loads((ROOT / "backend/app/api/schemas/chat_ws_v1/server.json").read_text())
    frames = json.loads((ROOT / "sdk/typescript/test/fixtures/chat-v1-recorded.json").read_text())["frames"]
    validator = Draft202012Validator(schema)
    for frame in frames: validator.validate(frame)
    assert [frame["seq"] for frame in frames] == list(range(len(frames)))
    assert frames[0]["type"] == "ready" and frames[-1]["type"] == "done"


def test_human_form_validation_is_bounded_and_preserves_legacy_answers():
    from app.services.run_service import human_response, RESPONSE_MAX
    form = {"approved": True, "note": "Đồng ý", "nested": {"values": [1, False, None]}}
    assert human_response(form, allow_form=True) == form and human_response(form, allow_form=True) is not form
    with pytest.raises(AppError): human_response(form)  # no opt-in on LangGraph/studio/inbox/channel APIs
    assert human_response(True) == "approved" and human_response(False) == "rejected"
    assert human_response("a" * RESPONSE_MAX) == "a" * RESPONSE_MAX
    for invalid in [{"x": "a" * RESPONSE_MAX}, {"x": float("nan")}, {"x": object()}, {"x": "\ud800"}, [], 12, None]:
        with pytest.raises(AppError) as error: human_response(invalid, allow_form=True)
        assert error.value.code == "RUN_RESPONSE_INVALID"
