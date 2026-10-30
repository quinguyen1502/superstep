"""TASK-0176 (REQ-0077, DEC-0072 decisions 2, 4, 5): "Include attachments" on LLM and Agent nodes. Documents reach the
model as text, images as image parts per provider, a model without vision gets a note, the mock names the files, and
the exports take the same field."""
import base64, json
import pytest
import respx
from app.engine import attachments, llm, providers
from app.engine import python_export as X, typescript_export as T
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from app.engine.validator import validate
from tests.chat_files import PNG
from tests.test_python_export import E, F, N, same_run

PDF_REC = {"id": "a1", "name": "invoice.pdf", "type": "application/pdf", "size": 900, "text": "Invoice 42 total 99 USD", "text_cut": False}
IMG_REC = {"id": "a2", "name": "shot.png", "type": "image/png", "size": len(PNG)}
FILES = [PDF_REC, IMG_REC]
B64 = base64.b64encode(PNG).decode()
load = lambda aid: ("image/png", PNG) if aid == "a2" else None  # noqa: E731


def body(route, i=0): return json.loads(route.calls[i].request.content)


def test_vision_is_per_provider_and_model():
    assert providers.vision("openai", "gpt-4o-mini") and providers.vision("anthropic", "claude-3-5-haiku-latest")
    assert providers.vision("openrouter", "openai/gpt-4o") and providers.vision("ollama", "llava:13b")
    assert not providers.vision("openai", "gpt-3.5-turbo") and not providers.vision("openai_compatible", "my-model")
    assert not providers.vision("typesafe", "gpt-4o") and not providers.vision("nope", "gpt-4o")


@respx.mock
def test_openai_and_anthropic_get_the_pdf_text_and_one_image_part():
    oa = respx.post("https://api.openai.com/v1/chat/completions").respond(json={"choices": [{"message": {"content": "ok"}}]})
    assert llm.call_llm("Summarise this", "gpt-4o-mini", {"provider": "openai", "api_key": "k"}, files=FILES, load=load) == "ok"
    content = body(oa)["messages"][0]["content"]
    assert content[0]["type"] == "text" and "Summarise this" in content[0]["text"] and 'Attached document "invoice.pdf"' in content[0]["text"]
    assert "Invoice 42" in content[0]["text"] and content[1:] == [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{B64}"}}]
    an = respx.post("https://api.anthropic.com/v1/messages").respond(json={"content": [{"type": "text", "text": "ok"}], "usage": {}})
    llm.call_llm("Summarise this", "claude-3-5-haiku-latest", {"provider": "anthropic", "api_key": "k"}, files=FILES, load=load)
    blocks = body(an)["messages"][0]["content"]
    assert "Invoice 42" in blocks[0]["text"] and blocks[1:] == [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": B64}}]
    # Agent calls: the same parts on the user message
    tools = [{"name": "add", "description": "", "parameters": {"type": "object"}}]
    llm.call_agent([{"role": "user", "content": "Look", "files": FILES}], tools, "claude-3-5-haiku-latest", {"provider": "anthropic", "api_key": "k"}, load=load)
    blocks = body(an, 1)["messages"][0]["content"]
    assert blocks[0]["type"] == "text" and "Invoice 42" in blocks[0]["text"] and blocks[1]["type"] == "image"
    lm = respx.post("http://localhost:1234/v1/chat/completions").respond(json={
        "choices": [{"message": {"role": "assistant", "content": "ok"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
    llm.call_agent([{"role": "user", "content": "Look", "files": FILES}], tools, "llava", {"provider": "lmstudio"}, load=load)
    parts = body(lm)["messages"][0]["content"]
    assert parts[0]["type"] == "text" and parts[1] == {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{B64}"}}


@respx.mock
def test_a_model_without_vision_gets_a_note_and_the_run_goes_on():
    oa = respx.post("https://api.openai.com/v1/chat/completions").respond(json={"choices": [{"message": {"content": "ok"}}]})
    assert llm.call_llm("Look", "gpt-3.5-turbo", {"provider": "openai", "api_key": "k"}, files=FILES, load=load) == "ok"
    content = body(oa)["messages"][0]["content"]
    assert isinstance(content, str) and attachments.NOTE.format(name="shot.png") in content and "Invoice 42" in content


def wf(t, include=True, **d):
    data = {"prompt": "{{state.message}}", "output_field": "reply", "include_attachments": include, **d}
    if t == "agent": data.update(tools=[{"name": "lookup_order", "description": "Find an order", "source": "builtin", "function": "lookup_order"}])
    return {"name": f"Files {t}", "state": [F("message"), F("reply"), F("files", "list")],
            "nodes": [N("start", "start"), N("n", t, **data), N("end", "end")], "edges": [E("start", "n"), E("n", "end")]}


def mock_run(w, inp):
    evs = list(run_stream(w, inp, ports=Ports(mock_models=True, attachment=load)))
    assert evs[-1]["type"] == "run_finished", evs[-1]
    return evs[-1]["state"]["reply"]


def test_the_mock_names_both_files_and_a_node_without_the_setting_gets_none():
    inp = {"message": "Summarise this", "files": FILES}
    assert mock_run(wf("llm"), inp).endswith("Attachments: document invoice.pdf, image shot.png")
    assert "Attachments" not in mock_run(wf("llm", include=False), inp)
    assert mock_run(wf("agent"), {"message": "hello", "files": FILES}).endswith("Attachments: document invoice.pdf, image shot.png")
    assert "Attachments" not in mock_run(wf("agent", include=False), {"message": "hello", "files": FILES})
    assert llm.call_llm("Hi", "m", None, mock=True, locale="vi", files=FILES).endswith("Tệp đính kèm: tài liệu invoice.pdf, ảnh shot.png")


def test_the_validator_checks_the_attachments_field():
    assert any("attachments field 'docs' is not in the state" in e for e in validate(wf("llm", attachments_field="docs")))
    assert any("must be a list field" in e for e in validate(wf("llm", attachments_field="message")))
    assert not [e for e in validate(wf("llm")) if "attachments" in e]


def test_exports_send_document_text_and_images_only_with_a_data_url(tmp_path):
    with_url = [PDF_REC, {**IMG_REC, "data_url": f"data:image/png;base64,{B64}"}]
    for t in ("llm", "agent"):
        same_run(tmp_path, wf(t), {"message": "Summarise this", "files": with_url})
        py, ts = X.to_python(wf(t), "Files", 1).code, T.to_typescript(wf(t), "Files", 1).code
        assert "with_files" in py and "data_url" in py and "withFiles" in ts and "data_url" in ts
        assert "call_llm_files" not in X.to_python(wf(t, include=False), "Files", 1).code
    text, images = attachments.build("P", with_url, True, None)
    assert "Invoice 42" in text and images == [{"name": "shot.png", "mime": "image/png", "data": B64}]
    text, images = attachments.build("P", FILES, True, None)  # no bytes and no data_url: a note
    assert images == [] and attachments.NOTE.format(name="shot.png") in text
