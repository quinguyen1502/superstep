"""Workflow templates (TASK-0025, DEC-0028): built-in starters, the sanitiser shared by save-as/export/import, and the
portable file format. Pure functions; persistence and permissions live in TemplateService."""
from __future__ import annotations
import copy

FORMAT, VERSION = "superstep/template", 1
FORMATS = (FORMAT, "langgraph-studio/template")  # files exported by v0.1.0 still import (TASK-0058)

# node data fields that point at per-user resources or secrets: never copied into a template
REF_FIELDS = ("credential_id", "knowledge_base_id", "server_id", "channel_id", "workflow_id")
SECRET_KEYS = ("headers", "api_key", "secret", "token", "password", "authorization")


def sanitize(wf: dict) -> dict:
    """The graph only (state, nodes, edges), with resource references blanked and secret-like keys and runtime `_` fields
    removed. The receiving user picks their own credential / knowledge base / server / channel / subgraph."""
    out = {"state": copy.deepcopy(wf.get("state") or []), "nodes": [], "edges": []}
    for n in wf.get("nodes") or []:
        d = {k: copy.deepcopy(v) for k, v in (n.get("data") or {}).items()
             if not k.startswith("_") and k.lower() not in SECRET_KEYS}
        for f in REF_FIELDS:
            if f in d: d[f] = ""
        if isinstance(d.get("tools"), list):  # an Agent node's tools point at servers and knowledge bases too (TASK-0119)
            d["tools"] = [{k: "" if k in REF_FIELDS else v for k, v in t.items() if not k.startswith("_") and k.lower() not in SECRET_KEYS}
                          if isinstance(t, dict) else t for t in d["tools"]]
        if isinstance(d.get("approval"), dict):  # a Human node keeps only the channel kind, not the connection, target or approvers (TASK-0064)
            a = d["approval"]; d["approval"] = {"channel": a["channel"]} if a.get("channel") else {}
            if isinstance(a.get("auto"), dict):  # AI review (TASK-0188): the policy stays, the judge's credential goes
                auto = copy.deepcopy(a["auto"]); judge = auto.get("judge")
                if isinstance(judge, dict): auto["judge"] = {**judge, "credential_id": ""}
                d["approval"]["auto"] = auto
        if isinstance(d.get("deadline"), dict):  # the timing stays, the escalation addresses go, like approvers (TASK-0066)
            d["deadline"] = {k: v for k, v in d["deadline"].items() if k != "escalate_to"}
        out["nodes"].append({"id": n["id"], "type": n["type"], "position": n.get("position") or {"x": 0, "y": 0}, "data": d})
    for e in wf.get("edges") or []:
        out["edges"].append({k: e[k] for k in ("id", "source", "target", "label", "conditional", "sourceHandle") if k in e and e[k] not in (None, "")})
    return out


def export_payload(name: str, description: str | None, graph: dict) -> dict:
    return {"format": FORMAT, "version": VERSION, "name": name, "description": description or "", "workflow": sanitize(graph)}


def problems(payload) -> list[str]:
    """Why an imported file is not a template (empty = fine). Structural only; the editor validates the graph on save."""
    if not isinstance(payload, dict): return ["not a JSON object"]
    errs = []
    if payload.get("format") not in FORMATS: errs.append(f"format must be {FORMAT!r}")
    if payload.get("version") != VERSION: errs.append(f"unsupported version {payload.get('version')!r}")
    wf = payload.get("workflow")
    if not isinstance(wf, dict): return errs + ["missing workflow"]
    nodes = wf.get("nodes") if isinstance(wf.get("nodes"), list) else None
    if nodes is None or not all(isinstance(n, dict) and n.get("id") and n.get("type") for n in nodes): return errs + ["nodes must be a list of {id, type}"]
    types = [n["type"] for n in nodes]
    if "start" not in types or "end" not in types: errs.append("a Start and an End node are required")
    ids = {n["id"] for n in nodes}
    if len(ids) != len(nodes): errs.append("node ids must be unique")
    for e in wf.get("edges") or []:
        if not isinstance(e, dict) or e.get("source") not in ids or e.get("target") not in ids: errs.append("every edge must connect existing nodes"); break
    return errs


def _n(i, t, x, y, **data): return {"id": i, "type": t, "position": {"x": x, "y": y}, "data": data}
def _e(i, s, t, label=None): return {"id": i, "source": s, "target": t, **({"label": label} if label else {})}


BUILTINS: list[dict] = [
    {"id": "builtin-chatbot", "name": "Chatbot", "description": "One LLM answers the user's message.", "workflow": {
        "state": [{"name": "message", "type": "string"}, {"name": "answer", "type": "string"}],
        "nodes": [_n("start", "start", 40, 160, label="Start"),
                  _n("reply", "llm", 300, 160, label="Reply", model="gpt-4o-mini", output_field="answer",
                     prompt="You are a helpful assistant. Answer briefly.\nUser: {{state.message}}"),
                  _n("end", "end", 560, 160, label="End")],
        "edges": [_e("e1", "start", "reply"), _e("e2", "reply", "end")]}},
    {"id": "builtin-rag", "name": "RAG Q&A", "description": "Retrieve passages from a knowledge base, then answer with them.", "workflow": {
        "state": [{"name": "message", "type": "string"}, {"name": "context", "type": "string"}, {"name": "answer", "type": "string"}],
        "nodes": [_n("start", "start", 40, 160, label="Start"),
                  _n("retrieve", "retriever", 280, 160, label="Search the FAQ", knowledge_base_id="", query="{{state.message}}", top_k=4, output_field="context"),
                  _n("answer", "llm", 540, 160, label="Answer from context", model="gpt-4o-mini", output_field="answer",
                     prompt="Answer using only this context.\n{{state.context}}\nQuestion: {{state.message}}"),
                  _n("end", "end", 800, 160, label="End")],
        "edges": [_e("e1", "start", "retrieve"), _e("e2", "retrieve", "answer"), _e("e3", "answer", "end")]}},
    {"id": "builtin-approval", "name": "Approval flow", "description": "Draft a reply, ask a human to approve it, then send or revise.", "workflow": {
        "state": [{"name": "message", "type": "string"}, {"name": "draft", "type": "string"}, {"name": "decision", "type": "string"}, {"name": "answer", "type": "string"}],
        "nodes": [_n("start", "start", 40, 180, label="Start"),
                  _n("draft", "llm", 260, 180, label="Draft reply", model="gpt-4o-mini", output_field="draft", prompt="Draft a reply to: {{state.message}}"),
                  _n("ask", "human", 500, 180, label="Supervisor approval", prompt="Approve this reply?\n{{state.draft}}", output_field="decision"),
                  _n("route", "condition", 740, 180, label="Approved?", field="decision", default="rejected"),
                  _n("send", "llm", 980, 80, label="Polish reply", model="gpt-4o-mini", output_field="answer", prompt="Polish this approved reply: {{state.draft}}"),
                  _n("end", "end", 1220, 180, label="End")],
        "edges": [_e("e1", "start", "draft"), _e("e2", "draft", "ask"), _e("e3", "ask", "route"),
                  _e("e4", "route", "send", "approved"), _e("e5", "route", "end", "rejected"), _e("e6", "send", "end")]}},
    {"id": "builtin-router", "name": "Router", "description": "Classify the request and route it to a specialised branch.", "workflow": {
        "state": [{"name": "message", "type": "string"}, {"name": "intent", "type": "string"}, {"name": "answer", "type": "string"}],
        "nodes": [_n("start", "start", 40, 200, label="Start"),
                  _n("classify", "llm", 260, 200, label="Classify", model="gpt-4o-mini", output_field="intent",
                     prompt="Reply with exactly one label: billing, technical or other.\n{{state.message}}"),
                  _n("route", "condition", 500, 200, label="Route", field="intent", default="other"),
                  _n("billing", "llm", 740, 60, label="Billing answer", model="gpt-4o-mini", output_field="answer", prompt="Answer the billing question: {{state.message}}"),
                  _n("technical", "llm", 740, 200, label="Technical answer", model="gpt-4o-mini", output_field="answer", prompt="Answer the technical question: {{state.message}}"),
                  _n("other", "llm", 740, 340, label="General answer", model="gpt-4o-mini", output_field="answer", prompt="Answer: {{state.message}}"),
                  _n("end", "end", 980, 200, label="End")],
        "edges": [_e("e1", "start", "classify"), _e("e2", "classify", "route"), _e("e3", "route", "billing", "billing"),
                  _e("e4", "route", "technical", "technical"), _e("e5", "route", "other", "other"),
                  _e("e6", "billing", "end"), _e("e7", "technical", "end"), _e("e8", "other", "end")]}},
]


def _s(*fields: str) -> list[dict]:
    """State fields: "name" is a string, "name:type" another type, "name:list+" a list with the append reducer."""
    out = []
    for f in fields:
        name, _, t = f.partition(":")
        out.append({"name": name, "type": (t or "string").rstrip("+"), **({"reducer": "append"} if t.endswith("+") else {})})
    return out


def _ask(i, x, y, label, prompt, field, kind=None, due=None):
    """A Human node. A channel template stores only the kind; the user picks the connection, target and approvers.
    due: (after, remind_every, on_timeout), the node's deadline (TASK-0066)."""
    return _n(i, "human", x, y, label=label, prompt=prompt, output_field=field, **({"approval": {"channel": kind}} if kind else {}),
              **({"deadline": dict(zip(("after", "remind_every", "on_timeout"), due))} if due else {}))


def _llm(i, x, y, label, prompt, field): return _n(i, "llm", x, y, label=label, model="gpt-4o-mini", output_field=field, prompt=prompt)
def _mail(i, x, y, label, to, subject, body, **kw): return _n(i, "email", x, y, label=label, to=to, subject=subject, body=body, format="text", **kw)
def _route(i, x, y, label, field, default="rejected"): return _n(i, "condition", x, y, label=label, field=field, default=default)
def _tool(name, description, source, **settings): return {"name": name, "description": description, "source": source, **settings}
def _choice(qid, instructions, *options):
    return {"id": qid, "type": "choice", "instructions": instructions, "field": qid, "options": [{"label": l, "description": d} for l, d in options]}


# Real processes, each on the channel that suits it (TASK-0064). Every Human node also waits in the studio until a
# connection is picked, and LLM / Decision nodes answer from the offline mocks without keys.
BUILTINS += [
    {"id": "builtin-refund-approval", "name": "Refund approval", "description": "Finance approves a customer's refund in Slack; the customer gets an e-mail either way.", "workflow": {
        "state": _s("request", "customer_email", "summary", "decision", "decline", "sent:object"),
        "nodes": [_n("start", "start", 40, 200, label="Start"),
                  _llm("summarize", 260, 200, "Summarise the request", "Summarise this refund request: order number, amount and reason.\n{{state.request}}", "summary"),
                  _ask("finance", 500, 200, "Finance approval", "Approve this refund?\n{{state.summary}}", "decision", "slack", due=("1d", "4h", "reject")),
                  _route("route", 740, 200, "Approved?", "decision"),
                  _mail("confirm", 980, 80, "E-mail the confirmation", "{{state.customer_email}}", "Your refund is approved",
                        "Good news: your refund is approved.\n\n{{state.summary}}", output_field="sent"),
                  _llm("decline_draft", 980, 320, "Draft a polite decline", "Write a short, polite e-mail declining this refund:\n{{state.summary}}", "decline"),
                  _mail("decline_mail", 1220, 320, "E-mail the decline", "{{state.customer_email}}", "About your refund request", "{{state.decline}}", output_field="sent"),
                  _n("end", "end", 1460, 200, label="End")],
        "edges": [_e("e1", "start", "summarize"), _e("e2", "summarize", "finance"), _e("e3", "finance", "route"),
                  _e("e4", "route", "confirm", "approved"), _e("e5", "route", "decline_draft", "rejected"),
                  _e("e6", "confirm", "end"), _e("e7", "decline_draft", "decline_mail"), _e("e8", "decline_mail", "end")]}},
    {"id": "builtin-leave-request", "name": "Leave request", "description": "A manager approves time off in Microsoft Teams; the employee and HR get the answer by e-mail.", "workflow": {
        "state": _s("message", "employee_email", "details", "decision", "sent:object"),
        "nodes": [_n("start", "start", 40, 180, label="Start"),
                  _llm("extract", 260, 180, "Read the request", "List the dates, the number of days and the reason in this leave request:\n{{state.message}}", "details"),
                  _ask("manager", 500, 180, "Manager approval", "Approve this leave?\n{{state.details}}", "decision", "teams", due=("2d", "1d", "reject")),
                  _mail("notify", 740, 180, "E-mail the employee and HR", "{{state.employee_email}}", "Your leave request: {{state.decision}}",
                        "Your leave request was {{state.decision}}.\n\n{{state.details}}", cc="hr@example.com", output_field="sent"),
                  _n("end", "end", 980, 180, label="End")],
        "edges": [_e("e1", "start", "extract"), _e("e2", "extract", "manager"), _e("e3", "manager", "notify"), _e("e4", "notify", "end")]}},
    {"id": "builtin-social-post", "name": "Social post review", "description": "An editor approves a post in Telegram, or sends it back with notes to rewrite.", "workflow": {
        "state": _s("brief", "post", "decision", "final"),
        "nodes": [_n("start", "start", 40, 200, label="Start"),
                  _llm("write", 260, 200, "Write the post", "Write a short social media post from this brief:\n{{state.brief}}", "post"),
                  _ask("editor", 500, 200, "Editor review", "Approve this post, or reply with what to change.\n{{state.post}}", "decision", "telegram", due=("1d", "4h", "approve")),
                  _route("route", 740, 200, "Approved?", "decision"),
                  _llm("finish", 980, 80, "Add hashtags", "Add two or three fitting hashtags to this post:\n{{state.post}}", "final"),
                  _llm("rewrite", 740, 380, "Rewrite with the notes", "Rewrite this post.\nNotes: {{state.decision}}\nPost: {{state.post}}", "post"),
                  _n("end", "end", 1220, 80, label="End")],
        "edges": [_e("e1", "start", "write"), _e("e2", "write", "editor"), _e("e3", "editor", "route"),
                  _e("e4", "route", "finish", "approved"), _e("e5", "route", "rewrite", "rejected"), _e("e6", "rewrite", "editor"), _e("e7", "finish", "end")]}},
    {"id": "builtin-large-order", "name": "Large order check", "description": "Risky orders wait for a sales manager in WhatsApp; the others go straight through.", "workflow": {
        "state": _s("order", "risk", "decision", "reply"),
        "nodes": [_n("start", "start", 40, 200, label="Start"),
                  _n("assess", "decision", 260, 200, label="Assess the order", model="jev-latest", text="{{state.order}}",
                     questions=[_choice("risk", "Does this order need a manager's check before it is processed?",
                                        ("review", "Unusual amount, a new customer or a changed delivery address"), ("auto", "A normal order"))]),
                  _route("risky", 500, 200, "Needs a check?", "risk", "review"),
                  _ask("manager", 740, 320, "Sales manager check", "Confirm this order?\n{{state.order}}", "decision", "whatsapp", due=("4h", "1h", "reject")),
                  _route("route", 980, 320, "Confirmed?", "decision"),
                  _llm("confirm", 1220, 80, "Confirm to the customer", "Write a short order confirmation for:\n{{state.order}}", "reply"),
                  _llm("cancel", 1220, 440, "Explain the cancellation", "Write a short, polite message cancelling this order:\n{{state.order}}", "reply"),
                  _n("end", "end", 1460, 200, label="End")],
        "edges": [_e("e1", "start", "assess"), _e("e2", "assess", "risky"), _e("e3", "risky", "confirm", "auto"), _e("e4", "risky", "manager", "review"),
                  _e("e5", "manager", "route"), _e("e6", "route", "confirm", "approved"), _e("e7", "route", "cancel", "rejected"),
                  _e("e8", "confirm", "end"), _e("e9", "cancel", "end")]}},
    {"id": "builtin-expense-claim", "name": "Expense claim", "description": "Check a travel expense against the policy, approve it by e-mail, then tell the employee.", "workflow": {
        "state": _s("claim", "employee_email", "check", "decision", "sent:object"),
        "nodes": [_n("start", "start", 40, 180, label="Start"),
                  _llm("check", 260, 180, "Check against the policy", "Check this expense claim against a policy of hotels up to $150 a night and meals up to $50 a day. List anything over the limit.\n{{state.claim}}", "check"),
                  _ask("approver", 500, 180, "Approve by e-mail", "Approve this expense claim?\n{{state.claim}}\n\nPolicy check: {{state.check}}", "decision", "email", due=("3d", "1d", "reject")),
                  _mail("notify", 740, 180, "E-mail the employee", "{{state.employee_email}}", "Your expense claim: {{state.decision}}",
                        "Your expense claim was {{state.decision}}.\n\n{{state.check}}", output_field="sent"),
                  _n("end", "end", 980, 180, label="End")],
        "edges": [_e("e1", "start", "check"), _e("e2", "check", "approver"), _e("e3", "approver", "notify"), _e("e4", "notify", "end")]}},
    {"id": "builtin-purchase-request", "name": "Purchase request", "description": "A team lead approves in Slack, then finance approves by e-mail; the requester hears back.", "workflow": {
        "state": _s("request", "requester_email", "summary", "lead_decision", "decision", "sent:object"),
        "nodes": [_n("start", "start", 40, 220, label="Start"),
                  _llm("summarize", 260, 220, "Summarise the request", "Summarise this purchase request: item, cost, supplier and why it is needed.\n{{state.request}}", "summary"),
                  _ask("lead", 500, 220, "Team lead approval", "Approve this purchase?\n{{state.summary}}", "lead_decision", "slack", due=("2d", "1d", "reject")),
                  _route("lead_ok", 740, 220, "Lead approved?", "lead_decision"),
                  _ask("finance", 980, 100, "Finance approval", "The team lead approved this purchase. Approve the budget?\n{{state.summary}}", "decision", "email", due=("3d", "1d", "reject")),
                  _route("finance_ok", 1220, 100, "Finance approved?", "decision"),
                  _mail("approved_mail", 1460, 0, "E-mail: approved", "{{state.requester_email}}", "Purchase approved", "Your purchase request is approved.\n\n{{state.summary}}", output_field="sent"),
                  _mail("rejected_mail", 1460, 340, "E-mail: not approved", "{{state.requester_email}}", "Purchase not approved", "Your purchase request was not approved.\n\n{{state.summary}}", output_field="sent"),
                  _n("end", "end", 1700, 220, label="End")],
        "edges": [_e("e1", "start", "summarize"), _e("e2", "summarize", "lead"), _e("e3", "lead", "lead_ok"),
                  _e("e4", "lead_ok", "finance", "approved"), _e("e5", "lead_ok", "rejected_mail", "rejected"), _e("e6", "finance", "finance_ok"),
                  _e("e7", "finance_ok", "approved_mail", "approved"), _e("e8", "finance_ok", "rejected_mail", "rejected"),
                  _e("e9", "approved_mail", "end"), _e("e10", "rejected_mail", "end")]}},
    {"id": "builtin-support-escalation", "name": "Support with escalation", "description": "Answer from a knowledge base; a support agent reviews the answers that are unsure.", "workflow": {
        "state": _s("message", "context", "answer", "verdict", "review"),
        "nodes": [_n("start", "start", 40, 200, label="Start"),
                  _n("retrieve", "retriever", 260, 200, label="Search the FAQ", knowledge_base_id="", query="{{state.message}}", top_k=4, output_field="context"),
                  _llm("answer", 500, 200, "Answer from context", "Answer using only this context.\n{{state.context}}\nQuestion: {{state.message}}", "answer"),
                  _n("check", "decision", 740, 200, label="Is the answer sure?", model="jev-latest", text="Question: {{state.message}}\nAnswer: {{state.answer}}",
                     questions=[_choice("verdict", "Does the answer fully resolve the question?",
                                        ("answered", "The answer resolves the question from the context"),
                                        ("escalate", "The answer is unsure, or the context does not cover the question"))]),
                  _route("route", 980, 200, "Escalate?", "verdict", "escalate"),
                  _ask("review", 1220, 320, "Support agent review", "Check this answer before it is sent:\n{{state.answer}}", "review"),
                  _n("end", "end", 1460, 200, label="End")],
        "edges": [_e("e1", "start", "retrieve"), _e("e2", "retrieve", "answer"), _e("e3", "answer", "check"), _e("e4", "check", "route"),
                  _e("e5", "route", "end", "answered"), _e("e6", "route", "review", "escalate"), _e("e7", "review", "end")]}},
    {"id": "builtin-feedback-digest", "name": "Customer feedback digest", "description": "Label each piece of feedback, write a report and e-mail it to the team.", "workflow": {
        "state": _s("feedback:list", "item", "labelled:list+", "report", "sent:object"),
        "nodes": [_n("start", "start", 40, 200, label="Start"),
                  _n("each", "foreach", 280, 200, label="Each piece of feedback", items_field="feedback", item_field="item", max_items=100),
                  _llm("label", 540, 60, "Label it", "Label this feedback as positive, negative or suggestion, then summarise it in one line:\n{{state.item}}", "labelled"),
                  _llm("report", 540, 340, "Write the report", "Write a short report from this labelled feedback, grouped by label:\n{{state.labelled | join(\"\\n\")}}", "report"),
                  _mail("send", 800, 340, "E-mail the team", "team@example.com", "Customer feedback digest", "{{state.report}}", output_field="sent"),
                  _n("end", "end", 1060, 340, label="End")],
        "edges": [_e("e1", "start", "each"), _e("e2", "each", "label", "each"), _e("e3", "label", "each"),
                  _e("e4", "each", "report", "done"), _e("e5", "report", "send"), _e("e6", "send", "end")]}},
]



# An Agent node (TASK-0119, REQ-0072): the model picks the tools; a refund waits for a person's approval first.
BUILTINS += [
    {"id": "builtin-support-agent", "name": "Support agent", "description": "An agent looks up orders and the refund policy; a person approves each refund it requests.", "workflow": {
        "state": _s("message", "answer", "steps:list"),
        "nodes": [_n("start", "start", 40, 200, label="Start"),
                  _n("agent", "agent", 280, 200, label="Support agent", model="gpt-4o-mini", max_rounds=6, output_field="answer", steps_field="steps",
                     system_prompt="You are the support agent of an online shop. Use the tools to look up orders and the refund policy. "
                                   "Request a refund only when the policy allows it, and say what you did.",
                     prompt="Help this customer. Message: {{state.message}}",
                     tools=[_tool("lookup_order", "Find the delivery status of an order", "builtin", function="lookup_order"),
                            _tool("search_refund_policy", "Search the refund policy", "knowledge", knowledge_base_id="", top_k=3),
                            _tool("request_refund", "Request a refund for an order that arrived broken or late", "builtin", function="request_refund",
                                  approval=True)],
                     deadline={"after": "1d", "on_timeout": "reject"}),
                  _n("end", "end", 560, 200, label="End")],
        "edges": [_e("e1", "start", "agent"), _e("e2", "agent", "end")]}},
]

# Workflows as Agent tools (TASK-0137, REQ-0073, DEC-0066): a supervisor Agent calls two specialist workflows, which
# are created with it ("helpers"). A tool's `helper` names the helper whose new id becomes its `workflow_id`.
def _desk(label, prompt, *tools):
    return {"state": _s("message", "answer"),
            "nodes": [_n("start", "start", 40, 200, label="Start"),
                      _n("agent", "agent", 280, 200, label=label, model="gpt-4o-mini", max_rounds=4, output_field="answer", prompt=prompt, tools=list(tools)),
                      _n("end", "end", 560, 200, label="End")],
            "edges": [_e("e1", "start", "agent"), _e("e2", "agent", "end")]}


BUILTINS += [
    {"id": "builtin-support-team", "name": "Support team",
     "description": "A supervisor agent hands each question to a specialist workflow: the order desk or the refund desk.",
     "helpers": [
         {"key": "orders", "name": "Order desk", "workflow": _desk("Order desk", "Answer this question about an order: {{state.message}}",
                                                                 _tool("lookup_order", "Find the delivery status of an order", "builtin", function="lookup_order"))},
         {"key": "refunds", "name": "Refund desk", "workflow": _desk("Refund desk", "Handle this refund request: {{state.message}}",
                                                                   _tool("request_refund", "Request a refund for an order that arrived broken or late", "builtin",
                                                                         function="request_refund", approval=True))}],
     "workflow": {
        "state": _s("message", "answer", "steps:list"),
        "nodes": [_n("start", "start", 40, 200, label="Start"),
                  _n("agent", "agent", 280, 200, label="Supervisor", model="gpt-4o-mini", max_rounds=4, output_field="answer", steps_field="steps",
                     system_prompt="You lead a support team. Hand each question to the desk that handles it, then answer the customer "
                                   "with what the desk found.",
                     prompt="Help this customer. Message: {{state.message}}",
                     tools=[_tool("order_desk", "Questions about where an order is", "workflow", helper="orders", workflow_id="",
                                  inputs=["message"], outputs=["answer"]),
                            _tool("refund_desk", "Refund requests for an order that arrived broken or late", "workflow", helper="refunds",
                                  workflow_id="", inputs=["message"], outputs=["answer"])]),
                  _n("end", "end", 560, 200, label="End")],
        "edges": [_e("e1", "start", "agent"), _e("e2", "agent", "end")]}},
]

# Test cases of each built-in template (TASK-0069, REQ-0042), in the shape of the workflow tests API. They pass with the
# offline mock model: a Condition takes the label it finds as a whole word, and the Decision mock the label it finds in the
# state, so the inputs name their branch. A workflow made from the template gets a copy; saved templates carry none.
def _case(name, inp, answers=None, *checks): return {"name": name, "input": inp, "answers": answers or {}, "checks": [OK, *checks]}
def _ran(node, ran=True): return {"kind": "node", "node": node, "ran": ran}
def _is(field, value): return {"kind": "field", "field": field, "op": "equals", "value": value}
def _filled(field): return {"kind": "field", "field": field, "op": "not_empty"}
def _has(field, text): return {"kind": "field", "field": field, "op": "contains", "value": text}
def _called(node, tool, called=True): return {"kind": "tool", "node": node, "tool": tool, "called": called}
OK = {"kind": "status", "value": "ok"}
YES, NO = ["approved"], ["rejected"]

TESTS: dict[str, list[dict]] = {
    "builtin-chatbot": [_case("Answers a question", {"message": "What are your opening hours?"}, None, _ran("reply"), _filled("answer"))],
    "builtin-rag": [_case("Answers from the knowledge base", {"message": "How long is the laptop warranty?"}, None, _ran("retrieve"), _filled("answer"))],
    "builtin-approval": [
        _case("Approved reply is polished", {"message": "Where is my order A100?"}, {"ask": YES}, _is("decision", "approved"), _ran("send"), _filled("answer")),
        _case("Rejected reply is not sent", {"message": "Where is my order A100?"}, {"ask": NO}, _is("decision", "rejected"), _ran("send", False))],
    "builtin-router": [
        _case("Billing question", {"message": "I was charged twice, this is a billing question"}, None, _ran("billing"), _ran("technical", False)),
        _case("Technical question", {"message": "The app crashes on start, a technical problem"}, None, _ran("technical"), _ran("billing", False)),
        _case("Anything else", {"message": "What are your opening hours?"}, None, _ran("other"), _filled("answer"))],
    "builtin-refund-approval": [
        _case("Approved refund is confirmed", {"request": "Refund order 1042, $80, the parcel arrived broken.", "customer_email": "ann@example.com"},
              {"finance": YES}, _is("decision", "approved"), _ran("confirm"), _ran("decline_draft", False), _filled("sent")),
        _case("Declined refund gets a polite e-mail", {"request": "Refund order 1043, $900, changed my mind after a year.", "customer_email": "bo@example.com"},
              {"finance": NO}, _is("decision", "rejected"), _ran("decline_mail"), _ran("confirm", False))],
    "builtin-leave-request": [
        _case("Approved leave", {"message": "I'd like leave from 3 to 5 March for a family event.", "employee_email": "bo@example.com"},
              {"manager": YES}, _is("decision", "approved"), _ran("notify"), _filled("sent")),
        _case("Rejected leave", {"message": "I'd like leave for the whole of December.", "employee_email": "bo@example.com"},
              {"manager": NO}, _is("decision", "rejected"), _ran("notify"))],
    "builtin-social-post": [
        _case("Approved post gets hashtags", {"brief": "Launch of our new dark mode"}, {"editor": YES}, _ran("rewrite", False), _filled("final")),
        _case("Rewritten with notes, then approved", {"brief": "Launch of our new dark mode"}, {"editor": ["Make it shorter", "approved"]},
              _ran("rewrite"), _filled("final"))],
    "builtin-large-order": [
        _case("Risky order confirmed by the manager", {"order": "Order 77: 40 laptops, new customer, delivery to a new address, needs a review"},
              {"manager": YES}, _is("risk", "review"), _ran("confirm"), _ran("cancel", False)),
        _case("Risky order cancelled by the manager", {"order": "Order 78: 60 phones, changed delivery address, needs a review"},
              {"manager": NO}, _ran("cancel"), _ran("confirm", False))],
    "builtin-expense-claim": [
        _case("Approved claim", {"claim": "Hotel $120 x 2 nights, meals $40", "employee_email": "bo@example.com"},
              {"approver": YES}, _is("decision", "approved"), _ran("notify"), _filled("check")),
        _case("Rejected claim", {"claim": "Hotel $480 x 3 nights, meals $200", "employee_email": "bo@example.com"},
              {"approver": NO}, _is("decision", "rejected"), _ran("notify"))],
    "builtin-purchase-request": [
        _case("Both approve", {"request": "Two monitors, $600, from Dell, for the new designers", "requester_email": "cy@example.com"},
              {"lead": YES, "finance": YES}, _ran("approved_mail"), _ran("rejected_mail", False)),
        _case("Team lead rejects", {"request": "A standing desk, $900", "requester_email": "cy@example.com"},
              {"lead": NO}, _ran("finance", False), _ran("rejected_mail")),
        _case("Finance rejects", {"request": "A conference trip, $4,000", "requester_email": "cy@example.com"},
              {"lead": YES, "finance": NO}, _ran("rejected_mail"), _ran("approved_mail", False))],
    "builtin-support-escalation": [
        _case("Sure answer goes straight out", {"message": "How long is the laptop warranty?"}, None, _is("verdict", "answered"), _ran("review", False), _filled("answer"))],
    "builtin-support-agent": [
        _case("Order status comes from the order tool", {"message": "Where is my order B200?"}, None,
              _called("agent", "lookup_order"), _called("agent", "request_refund", False), _has("answer", "In transit")),
        _case("Approved refund is requested", {"message": "Order A100 arrived broken, please refund it"}, {"agent": YES},
              _called("agent", "request_refund"), _has("answer", "Refund requested for order A100")),
        _case("Rejected refund is not requested", {"message": "Order A100 arrived broken, please refund it"}, {"agent": NO},
              _called("agent", "request_refund", False), _has("answer", "Rejected by a reviewer"))],
    "builtin-support-team": [
        _case("Order questions go to the order desk", {"message": "Where is my order B200?"}, None,
              _called("agent", "order_desk"), _called("agent", "refund_desk", False), _has("answer", "In transit")),
        # the refund desk asks a person before a refund; a test run answers no question inside a called workflow
        _case("Refund requests go to the refund desk", {"message": "Order A100 arrived broken, please refund it"}, None,
              _called("agent", "refund_desk"), _called("agent", "order_desk", False))],
    "builtin-feedback-digest": [
        _case("Three pieces of feedback make one report", {"feedback": ["Love the new editor", "Runs are slow on Mondays", "Please add a Discord channel"]},
              None, _ran("send"), _filled("report"), _filled("sent"))],
}
for _b in BUILTINS: _b["tests"] = TESTS[_b["id"]]

BUILTIN_IDS = {b["id"] for b in BUILTINS}
