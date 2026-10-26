"""Decision nodes (TASK-0050, DEC-0039): ask TypeSafe's Jev typed questions about the state.

Node data: `credential_id` (a TypeSafe credential), `model` (default `jev-latest`), `text` (a template; exactly one
`{{state.x}}` sends the value with its type, e.g. an object), `questions`, and optional `output_field` (an object field
that receives every answer). Each question has an `id`, a `type` and `instructions` (a template):
- `choice` with `options` [{label, description}] (2-255): the answer is the most likely label;
- `score` with `levels` [text, ...] from low to high (2-10): the answer is a number from 0 to the top level index;
- `noul`: the answer is a number from 0 (false) to 1 (true).
A question's optional `field` receives that answer, so a Condition can branch on a choice directly.
Without a credential the node uses TYPESAFE_API_KEY, else a deterministic offline mock (like LLM nodes).
"""
from __future__ import annotations
import os, re
from typing import Any, Callable, Dict, List, Optional
from . import providers
from .issues import Issue
from .templating import render, render_args
from .usage import estimate_tokens, make_usage

TYPES = ("choice", "score", "noul")
DEFAULT_MODEL = "jev-latest"
MAX_QUESTIONS, OPTIONS, LEVELS = 20, (2, 255), (2, 10)
ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
FIELD_TYPES = {"choice": ("string",), "score": ("number",), "noul": ("number",)}
MAIN = {"choice": "choice", "score": "score", "noul": "noul"}  # the answer key that goes to a question's field


def questions_of(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    q = d.get("questions")
    return [x for x in q if isinstance(x, dict)] if isinstance(q, list) else []


def fields(d: Dict[str, Any]) -> List[str]:
    """State fields this node writes."""
    return [f for f in [d.get("output_field")] + [q.get("field") for q in questions_of(d)] if f]


def templates(d: Dict[str, Any]) -> List[str]:
    return [d.get("text") or ""] + [q.get("instructions") or "" for q in questions_of(d) if isinstance(q.get("instructions"), str)]


def build(d: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """The System One request body for this node and state."""
    qs = {}
    for q in questions_of(d):
        item: Dict[str, Any] = {"type": q["type"], "instructions": render(q.get("instructions") or "", state)}
        if q["type"] == "choice": item["criteria"] = {o["label"]: (o.get("description") or None) for o in q.get("options") or []}
        if q["type"] == "score": item["criteria"] = list(q.get("levels") or [])
        qs[q["id"]] = item
    return {"state": render_args(d.get("text") or "", state), "model": d.get("model") or DEFAULT_MODEL, "questions": qs}


def mock(body: Dict[str, Any]) -> Dict[str, Any]:
    """Offline answers: the first choice label found in the state text (else the first), the lowest score, noul 0.5."""
    text = str(body.get("state")).casefold(); answers = {}
    for qid, q in body["questions"].items():
        if q["type"] == "choice":
            labels = list(q["criteria"])
            pick = next((l for l in labels if re.search(rf"(?<!\w){re.escape(l.casefold())}(?!\w)", text)), labels[0])
            answers[qid] = {"type": "choice", "choice": pick, "confidence": 1.0, "probabilities": {l: float(l == pick) for l in labels}}
        elif q["type"] == "score":
            n = len(q["criteria"])
            answers[qid] = {"type": "score", "score": 0.0, "confidence": 1.0, "legend": {str(i): q["criteria"][i] for i in range(n)},
                            "probabilities": {str(i): float(i == 0) for i in range(n)}}
        else:
            answers[qid] = {"type": "noul", "noul": 0.5}
    return {"model": "jev-mock", "answers": answers, "usage": {"input_tokens": estimate_tokens(str(body)), "output_tokens": 0}}


def ask(body: Dict[str, Any], cred: Optional[Dict[str, Any]], report: Callable[[Dict[str, Any]], None], offline: bool = False) -> Dict[str, Any]:
    if offline: cred = None  # test run with the offline mock (TASK-0067)
    elif cred is None and (key := os.environ.get("TYPESAFE_API_KEY")):
        cred = {"provider": "typesafe", "api_key": key, "base_url": os.environ.get("TYPESAFE_BASE_URL")}
    if cred is None:
        data = mock(body); u = data["usage"]
        report(make_usage("mock", body["model"], u["input_tokens"], 0, estimated=True)); return data
    p = providers.get(cred.get("provider") or "")
    if not isinstance(p, providers.TypeSafe):
        raise providers.LLMError(f"Decision nodes need a TypeSafe credential (this one is {cred.get('provider')})")
    data = p.decide(body, cred); u = data.get("usage") or {}
    report(make_usage(p.id, str(data.get("model") or body["model"]), int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)))
    return data


def node_fn(node: Dict[str, Any], resolve=None, usage=None, offline: bool = False) -> Callable[[dict], dict]:
    nid, d = node["id"], node.get("data") or {}

    def fn(state):
        cred = None
        if d.get("credential_id") and not offline:
            if resolve is None: raise providers.LLMError("Node uses a credential but no resolver is available")
            cred = resolve(d["credential_id"])
        body = build(d, state)
        data = ask(body, cred, (lambda u: usage(nid, u)) if usage else (lambda u: None), offline)
        answers = data["answers"]; out: Dict[str, Any] = {}
        for q in questions_of(d):
            a = answers.get(q["id"])
            if not isinstance(a, dict): raise providers.ProviderError("PROVIDER_BAD_RESPONSE", "typesafe", f"no answer for question {q['id']}")
            if q.get("field"): out[q["field"]] = a.get(MAIN[q["type"]])
        if d.get("output_field"): out[d["output_field"]] = answers
        return out
    return fn


def errors(nid: str, d: Dict[str, Any], schema: List[dict]) -> List[str]:
    errs: List[str] = []; by = {f["name"]: f for f in schema}
    qs = d.get("questions")
    if not isinstance(qs, list) or not qs: return [Issue("DECISION_QUESTIONS_MISSING", node=nid)]
    if len(qs) > MAX_QUESTIONS: errs.append(Issue("DECISION_QUESTIONS_MANY", node=nid, max=MAX_QUESTIONS))
    if not isinstance(d.get("text"), str) or not d["text"].strip(): errs.append(Issue("DECISION_TEXT_EMPTY", node=nid))
    seen = set()
    for i, q in enumerate(qs, 1):
        if not isinstance(q, dict): errs.append(Issue("DECISION_QUESTION_NOT_OBJECT", node=nid, index=i)); continue
        qid, t = q.get("id"), q.get("type"); name = {"node": nid, "question": qid or i}
        if not isinstance(qid, str) or not ID_RE.match(qid): errs.append(Issue("DECISION_QUESTION_ID", **name))
        elif qid in seen: errs.append(Issue("DECISION_QUESTION_DUPLICATE", node=nid, question=qid))
        seen.add(qid)
        if t not in TYPES: errs.append(Issue("DECISION_QUESTION_TYPE", **name, types=", ".join(TYPES))); continue
        if not isinstance(q.get("instructions"), str) or not q["instructions"].strip(): errs.append(Issue("DECISION_INSTRUCTIONS_EMPTY", **name))
        if t == "choice":
            labels = [o.get("label") if isinstance(o, dict) else None for o in (q.get("options") if isinstance(q.get("options"), list) else [])]
            if not OPTIONS[0] <= len(labels) <= OPTIONS[1]: errs.append(Issue("DECISION_OPTIONS_COUNT", **name, min=OPTIONS[0], max=OPTIONS[1]))
            if any(not isinstance(l, str) or not l.strip() for l in labels): errs.append(Issue("DECISION_OPTION_LABEL", **name))
            elif len(set(labels)) != len(labels): errs.append(Issue("DECISION_OPTION_LABELS_SAME", **name))
        if t == "score":
            levels = q.get("levels") if isinstance(q.get("levels"), list) else []
            if not LEVELS[0] <= len(levels) <= LEVELS[1]: errs.append(Issue("DECISION_LEVELS_COUNT", **name, min=LEVELS[0], max=LEVELS[1]))
            if any(not isinstance(l, str) or not l.strip() for l in levels): errs.append(Issue("DECISION_LEVEL_EMPTY", **name))
        if (fld := q.get("field")) and schema:
            f = by.get(fld)
            if f is None: errs.append(Issue("DECISION_FIELD_UNKNOWN", **name, field=fld))
            elif f.get("type", "string") not in FIELD_TYPES[t]: errs.append(Issue("DECISION_FIELD_TYPE", **name, field=fld, types=" or ".join(FIELD_TYPES[t])))
            elif (f.get("reducer") or "replace") != "replace": errs.append(Issue("DECISION_FIELD_REDUCER", **name, field=fld))
    of = d.get("output_field")
    if of and schema:
        f = by.get(of)
        if f is None: errs.append(Issue("DECISION_OUTPUT_UNKNOWN", node=nid, field=of))
        elif f.get("type", "string") != "object": errs.append(Issue("DECISION_OUTPUT_TYPE", node=nid, field=of))
    if not fields(d): errs.append(Issue("DECISION_FIELDS_MISSING", node=nid))
    return errs
