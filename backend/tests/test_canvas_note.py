"""A canvas note is text for people. It is not a node the run executes."""
from app.engine.compiler import compile_workflow
from app.engine.runtime import run_stream
from app.engine.validator import validate


def N(i, t, **d):
    return {"id": i, "type": t, "data": {"label": i, **d}}


def E(i, s, t):
    return {"id": i, "source": s, "target": t}


def graph(notes=None):
    nodes = [N("start", "start"), N("end", "end"), *(notes or [])]
    return {"state": [{"name": "message", "type": "string"}], "nodes": nodes,
            "edges": [E("e1", "start", "end")]}


def test_loose_notes_are_valid_including_empty_text():
    w = graph([
        N("n1", "note", text=""),
        {"id": "n2", "type": "note", "data": {}},
        N("n3", "note", text="Remember the refund path"),
    ])
    assert validate(w) == []


def test_an_edge_that_touches_a_note_names_the_note():
    w = graph([N("n1", "note", label="Refund path", text="x")])
    w["edges"].append(E("in", "start", "n1"))
    named = [e for e in validate(w) if "n1" in e and "Refund path" in e]
    assert named and all("not reachable" not in e for e in named)
    w = graph([N("n1", "note", label="Refund path")])
    w["edges"].append(E("out", "n1", "end"))
    assert any("n1" in e and "Refund path" in e for e in validate(w))


def test_compile_skips_notes_and_the_run_does_not_emit_them():
    w = graph([N("n1", "note", text=""), N("n2", "note", text="hello")])
    app = compile_workflow(w)
    assert "n1" not in app.nodes and "n2" not in app.nodes
    evs = list(run_stream(w, {"message": "hi"}))
    assert [e.get("node") for e in evs if e["type"] == "node_finished"] == ["start", "end"]
    assert evs[-1]["type"] == "run_finished"
    assert all(e.get("node") not in {"n1", "n2"} for e in evs)
