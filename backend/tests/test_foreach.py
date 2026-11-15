"""For each node — run a branch once per list item, one at a time."""
import copy
import pytest
from app.engine import foreach
from app.engine.effects import Effects
from app.engine.runtime import run_stream
from app.engine.tools import register_tool
from app.engine.validator import validate

KEYS = []


@register_tool("fe_upper")
def _upper(state):
    """test helper: the current item in upper case"""
    return str(state.get("item")).upper()


@register_tool("fe_keyed")
def _keyed(state, idempotency_key=None):
    """test helper: records the idempotency key"""
    KEYS.append(idempotency_key); return state.get("item")


@register_tool("fe_row")
def _row(state):
    """test helper: the current number times ten"""
    return state.get("n", 0) * 10


def N(i, t, **d): return {"id": i, "type": t, "data": {"label": i, **d}}
def E(i, s, t, label=None): return {"id": i, "source": s, "target": t, **({"label": label} if label else {})}
STATE = [{"name": "items", "type": "list"}, {"name": "item", "type": "string"}, {"name": "i", "type": "integer"},
         {"name": "results", "type": "list", "reducer": "append"}, {"name": "answer", "type": "string"}]


def loop_wf(body=None, **fe):
    body = body or [N("work", "tool", function="fe_upper", output_field="results")]
    nodes = [N("s", "start"), N("fe", "foreach", items_field="items", item_field="item", index_field="i", **fe), *body, N("e", "end")]
    chain = [b["id"] for b in body]
    edges = [E("1", "s", "fe"), E("2", "fe", chain[0], "each"), E("3", "fe", "e", "done"), E("4", chain[-1], "fe")]
    edges += [E(f"b{k}", a, b) for k, (a, b) in enumerate(zip(chain, chain[1:]))]
    return {"name": "t", "state": copy.deepcopy(STATE), "nodes": nodes, "edges": edges}


def run(wf, inputs, **kw): return list(run_stream(wf, inputs, **kw))
def final(evs): return next(e for e in evs if e["type"] == "run_finished")["state"]


# ---------- running ----------
def test_runs_the_body_once_per_item_in_order():
    evs = run(loop_wf(), {"items": ["a", "b", "c"]})
    st = final(evs)
    assert st["results"] == ["A", "B", "C"] and st["item"] == "c" and st["i"] == 2
    assert not any(k.startswith(foreach.PREFIX) for k in st)  # loop positions stay internal
    assert [e["iteration"] for e in evs if e["type"] == "node_started" and e["node"] == "work"] == [1, 2, 3]
    assert [e["iteration"] for e in evs if e["type"] == "node_started" and e["node"] == "fe"] == [1, 2, 3, 4]  # the 4th visit leaves


@pytest.mark.parametrize("items", [[], None])
def test_empty_or_missing_list_goes_straight_to_done(items):
    evs = run(loop_wf(), {"items": items} if items is not None else {})
    assert not [e for e in evs if e.get("node") == "work"] and evs[-1]["type"] == "run_finished"


def test_not_a_list_and_too_many_items_are_node_errors():
    fn = foreach.node_fn(N("fe", "foreach", items_field="items", item_field="item"))  # e.g. an LLM wrote text to the list field
    with pytest.raises(ValueError, match=r"state.items must be a list \(got dict\)"): fn({"items": {"a": 1}})
    err = run(loop_wf(max_items=2), {"items": ["a", "b", "c"]})[-1]
    assert err["type"] == "error" and "3 items, more than the limit of 2" in err["errors"][0]


def test_long_lists_get_enough_steps():
    body = [N("w1", "tool", function="fe_upper", output_field="answer"), N("w2", "tool", function="fe_upper", output_field="results")]
    st = final(run(loop_wf(body), {"items": [str(n) for n in range(60)]}))  # ~180 steps, far above the base limit of 25
    assert len(st["results"]) == 60


def test_each_item_gets_its_own_idempotency_key():
    KEYS.clear()
    run(loop_wf([N("work", "tool", function="fe_keyed", output_field="results")]), {"items": ["x", "y"]}, effects=Effects(run_id="r1"))
    assert len(KEYS) == 2 and KEYS[0] != KEYS[1] and all(KEYS)


def test_human_pause_inside_the_loop_resumes_at_the_same_item():
    w = loop_wf([N("ask", "human", prompt="ok {{state.item}}?", output_field="results")])
    evs = run(w, {"items": ["a", "b"]})
    wait = evs[-1]; assert wait["type"] == "run_waiting" and wait["prompt"] == "ok a?"
    evs = run(w, {}, resume={**wait["checkpoint"], "value": "yes a"})
    wait = evs[-1]; assert wait["type"] == "run_waiting" and wait["prompt"] == "ok b?"
    st = final(run(w, {}, resume={**wait["checkpoint"], "value": "yes b"}))
    assert st["results"] == ["yes a", "yes b"]


def test_nested_loops_restart_the_inner_list():
    state = [{"name": "rows", "type": "list"}, {"name": "row", "type": "list"}, {"name": "n", "type": "integer"},
             {"name": "results", "type": "list", "reducer": "append"}]
    nodes = [N("s", "start"), N("outer", "foreach", items_field="rows", item_field="row"), N("inner", "foreach", items_field="row", item_field="n"),
             N("w", "tool", function="fe_row", output_field="results"), N("e", "end")]
    edges = [E("1", "s", "outer"), E("2", "outer", "inner", "each"), E("3", "outer", "e", "done"),
             E("4", "inner", "w", "each"), E("5", "w", "inner"), E("6", "inner", "outer", "done")]
    wf = {"name": "t", "state": state, "nodes": nodes, "edges": edges}
    assert validate(wf) == []
    assert final(run(wf, {"rows": [[1, 2], [3], [], [4, 5]]}))["results"] == [10, 20, 30, 40, 50]


# ---------- validation ----------
def has(errs, frag): return any(frag in e for e in errs), errs


def test_valid_loop_needs_no_condition():
    assert validate(loop_wf()) == []


def test_each_and_done_are_not_parallel_branches():
    w = loop_wf(); w["nodes"].append(N("after", "tool", function="fe_upper", output_field="results"))
    w["edges"][2] = E("3", "fe", "after", "done"); w["edges"].append(E("5", "after", "e"))
    w["state"][3].pop("reducer")  # both routes write results without a reducer: fine, they never run together
    assert validate(w) == []


@pytest.mark.parametrize("mutate,frag", [
    (lambda w: w["nodes"][1]["data"].pop("items_field"), "choose the list field"),
    (lambda w: w["nodes"][1]["data"].update(items_field="item"), "list field 'item' must be of type list"),
    (lambda w: w["nodes"][1]["data"].update(item_field="ghost"), "item field 'ghost' is not in the state"),
    (lambda w: w["nodes"][1]["data"].update(item_field="results"), "item field 'results' must not have a reducer"),
    (lambda w: w["nodes"][1]["data"].update(index_field="item"), "index field 'item' must be of type integer or number"),
    (lambda w: w["nodes"][1]["data"].update(item_field="items"), "must be different fields"),
    (lambda w: w["nodes"][1]["data"].update(max_items=0), "max items must be an integer from 1 to 1000"),
    (lambda w: w["edges"][1].update(label="loop"), "needs exactly one 'each' edge"),
    (lambda w: w["edges"].pop(2), "needs exactly one 'each' edge"),
    (lambda w: w["edges"].__setitem__(3, E("4", "work", "e")), "must lead back to this For each node"),
    (lambda w: w["state"].append({"name": "loop:x", "type": "integer"}), "reserved for For each loops"),
])
def test_validation_errors(mutate, frag):
    w = loop_wf(); mutate(w)
    ok, errs = has(validate(w), frag); assert ok, errs


def test_step_budget():
    assert foreach.step_budget({"nodes": [N("s", "start")], "edges": []}) == 0
    assert foreach.step_budget(loop_wf(max_items=10)) == 10 * 2 + 1
