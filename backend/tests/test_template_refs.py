"""`{{state.field}}` paths and filters."""
import pytest
from app.core.errors import AppError
from app.engine.runtime import run_stream
from app.engine.templating import ref_errors, refs, render, render_args
from app.engine.validator import validate

ST = {"name": "  Ada ", "order": {"id": "A1", "items": [{"sku": "x"}, {"sku": "y"}]}, "tags": ["a", "b"], "n": 3, "none": None, "long": "abcdefghij"}


def test_plain_references_render_as_before():
    assert render("Hi {{state.name}} / {{ state.n }} / {{state.order}} / {{state.missing}}", ST) == \
        'Hi   Ada  / 3 / {"id": "A1", "items": [{"sku": "x"}, {"sku": "y"}]} / '


def test_paths_walk_dicts_and_lists():
    assert render("{{state.order.id}} {{state.order.items.1.sku}} {{state.tags.0}}", ST) == "A1 y a"
    assert render("[{{state.order.items.9.sku}}][{{state.order.nope}}][{{state.n.x}}]", ST) == "[][][]"  # missing -> empty


def test_filters():
    assert render("{{state.name | trim | upper}}", ST) == "ADA"
    assert render("{{ state.name|lower }}", ST) == "  ada "
    assert render("{{state.tags | join(\", \")}} {{state.tags | length}} {{state.order.items | length}}", ST) == "a, b 2 2"
    assert render("{{state.tags | first}}{{state.tags | last}}", ST) == "ab"
    assert render("{{state.none | default('n/a')}} {{state.missing | default(\"-\")}} {{state.n | default('x')}}", ST) == "n/a - 3"
    assert render("{{state.long | truncate(5)}} {{state.n | truncate(5)}}", ST) == "abcd… 3"
    assert render("{{state.name | json}}", ST) == '"  Ada "'


def test_exact_reference_in_tool_arguments_keeps_its_type():
    assert render_args({"n": "{{state.tags | length}}", "o": "{{state.order.items.0}}", "s": "x={{state.n}}"}, ST) == \
        {"n": 2, "o": {"sku": "x"}, "s": "x=3"}


def test_bad_filters_are_reported_and_refused_at_run_time():
    assert ref_errors(refs("{{state.a | shout}}")[0]) == ["unknown filter 'shout'"]
    assert ref_errors(refs("{{state.a | upper(1)}}")[0]) == ["filter 'upper' takes no argument"]
    assert ref_errors(refs("{{state.a | truncate('x')}}")[0]) == ["filter 'truncate' needs a number argument"]
    assert ref_errors(refs("{{state.a | default}}")[0]) == ["filter 'default' needs a text argument"]
    with pytest.raises(AppError) as e: render("{{state.a | shout}}", {})
    assert e.value.code == "TEMPLATE_REF_INVALID" and "shout" in e.value.message


def test_text_that_is_not_a_reference_stays_as_is():
    assert render("{{state.}} {{state.a | }} {{ state.a | f(x) }} {{name}}", {"a": 1}) == "{{state.}} {{state.a | }} {{ state.a | f(x) }} {{name}}"


def N(i, t, **d): return {"id": i, "type": t, "data": {"label": i, **d}}
def E(i, s, t): return {"id": i, "source": s, "target": t}
def wf(mid): return {"name": "t", "state": [{"name": "message", "type": "string"}, {"name": "out", "type": "string"}],
                     "nodes": [N("s", "start"), mid, N("e", "end")], "edges": [E("1", "s", mid["id"]), E("2", mid["id"], "e")]}


@pytest.mark.parametrize("node", [
    N("h", "human", prompt="{{state.message | shout}}", output_field="out"),
    N("t", "tool", mode="http", method="GET", url="https://example.com/{{state.message | shout}}", body="", output_field="out"),
    N("t", "tool", mode="http", method="POST", url="https://example.com", body='{"a": "{{state.message | shout}}"}', output_field="out"),
    N("m", "mcp", server_id="s1", tool="t", arguments={"a": {"b": ["{{state.message | shout}}"]}}, output_field="out"),
    N("l", "llm", prompt="{{state.message | shout}}", output_field="out"),
])
def test_validator_checks_every_template_field(node):
    assert any("unknown filter 'shout'" in e for e in validate(wf(node))), validate(wf(node))


def test_validator_checks_the_root_field_of_a_path():
    errs = validate(wf(N("h", "human", prompt="{{state.order.id}} {{state.message.x | upper}}", output_field="out")))
    assert errs == ["Node h: variable state.order is not in the state"], errs


def test_run_renders_paths_and_filters():
    w = wf(N("h", "human", prompt="Approve {{state.message | trim | upper}}?", output_field="out"))
    waiting = [e for e in run_stream(w, {"message": " refund "}) if e["type"] == "run_waiting"]
    assert waiting and waiting[0]["prompt"] == "Approve REFUND?"


def test_shared_cases_match_the_frontend_copy():
    """`frontend/src/lib/__tests__/state-refs.test.ts` reads the same file, so both patterns agree."""
    import json, pathlib
    for case in json.loads((pathlib.Path(__file__).parent / "fixtures" / "template_refs.json").read_text()):
        got = [{"field": r.field, "path": r.path, "filters": [list(f) for f in r.filters]} for r in refs(case["text"])]
        assert got == case["refs"], case["text"]
