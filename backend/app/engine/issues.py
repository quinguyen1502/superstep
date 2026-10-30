"""Validation messages with a code (TASK-0132, DEC-0065).

Every static check of a workflow reports an `Issue`: a `str` holding the English message, as before, plus a `code` and
its `params`. Lists of issues stay lists of strings for every caller (tests, SDKs, MCP, exports). The API sends
`issues_of(errors)` next to `errors`, and the editor translates by code (`validation.<CODE>` in the locales), falling
back to the English text. `MESSAGES` is the one English source; `tests/test_validation_messages.py` keeps
`locales/en.json` equal to it and `vi.json` in step.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

_NODE = "Node {node}: "
_AGENT_TOOL = "Agent node {node}: tool {tool}: "
_DECISION = "Decision node {node}: "
_QUESTION = "Decision node {node}, question {question}: "
_EMAIL = "Send email node {node}: "
_FOREACH = "For each node {node}: "
_HUMAN = "Human node {node}: "
_SUBGRAPH = "Subgraph node {node}: "

# Problems found in a node's code, and in a template reference's filters. at_node() adds the node, as NODE_<code>, and
# the reference, as NODE_REF_<code>; only those reach the API.
CODE_INNER = {
    "CODE_LANGUAGE_OFF": "{language} is not available on this server",
    "CODE_EMPTY": "the code is empty",
    "CODE_TOO_LARGE": "the code is larger than {kb} KB",
}
REF_INNER = {
    "FILTER_UNKNOWN": "unknown filter '{filter}'",
    "FILTER_NO_ARGUMENT": "filter '{filter}' takes no argument",
    "FILTER_NEEDS_TEXT": "filter '{filter}' needs a text argument",
    "FILTER_NEEDS_NUMBER": "filter '{filter}' needs a number argument",
}
INNER = {**CODE_INNER, **REF_INNER}

MESSAGES: Dict[str, str] = {
    # graph
    "NODE_ID_MISSING": "Every node needs an id",
    "EDGE_ENDS_MISSING": "Every edge needs a source and a target",
    "DUPLICATE_NODE_ID": "Duplicate node id: {ids}",
    "DUPLICATE_EDGE_ID": "Duplicate edge id: {ids}",
    "START_MISSING": "Exactly one Start node is required (none found)",
    "START_MANY": "Only one Start node is allowed (found {count}: {ids})",
    "END_MISSING": "At least one End node is required",
    "START_INCOMING": "Start must not have incoming edges",
    "END_OUTGOING": "End node {node} must not have outgoing edges",
    "EDGE_NODE_MISSING": "Edge {edge} points to a missing node: {nodes}",
    "NODE_SELF_LOOP": _NODE + "cannot connect to itself (only a Condition may create a loop)",
    "NODE_TYPE_INVALID": _NODE + "invalid type '{type}'",
    "NOTE_CONNECTED": "Note {node} ({label}) cannot be connected",
    "NODE_NO_OUTGOING": "Node {node} ({label}) has no outgoing edge",
    "NODE_UNREACHABLE": "Node {node} is not reachable from Start",
    "LOOP_WITHOUT_EXIT": "Loop without a Condition or For each: {path}",
    "PARALLEL_WRITES": "Parallel nodes {nodes} all write state.{field}: give the field a reducer (append, merge or add) or use different fields",
    # state
    "FIELD_RESERVED_FOREACH": "State field {field}: names starting with '{prefix}' are reserved for For each loops",
    "FIELD_RESERVED_AGENT": "State field {field}: names starting with '{prefix}' are reserved for Agent nodes",
    "REDUCER_UNKNOWN": "State field {field}: unknown reducer '{reducer}' (use {reducers})",
    "REDUCER_TYPE": "State field {field}: reducer '{reducer}' needs type {types}",
    # any node
    "OUTPUT_FIELD_MISSING": _NODE + "output_field is missing",
    "OUTPUT_FIELD_UNKNOWN": _NODE + "output_field '{field}' is not in the state",
    "VARIABLE_UNKNOWN": _NODE + "variable state.{field} is not in the state",
    "INPUT_FIELDS_INVALID": _NODE + "input fields must be a list of state field names",
    "INPUT_FIELD_UNKNOWN": _NODE + "input field '{field}' is not in the state",
    "RETRY_INVALID": _NODE + "retry must be an object with max_attempts and initial_interval",
    "RETRY_ATTEMPTS": _NODE + "retry attempts must be an integer from {min} to {max}",
    "RETRY_WAIT": _NODE + "retry wait must be a number of seconds greater than 0 and at most {max}",
    "TIMEOUT_INVALID": _NODE + "timeout must be a number of seconds greater than 0 and at most {max}",
    "CACHE_TTL_INVALID": _NODE + "cache TTL must be an integer number of seconds from {min} to {max}",
    "NODE_PROBLEM": _NODE + "{detail}",
    "NODE_REF_PROBLEM": _NODE + "{detail} in {ref}",
    # Tool, Condition, Join, Retriever, MCP, Subgraph, Human
    "FUNCTION_UNKNOWN": _NODE + "function '{function}' is not registered",
    "URL_MISSING": _NODE + "URL is missing",
    "CONDITION_FIELD_MISSING": _NODE + "Condition field is missing",
    "CONDITION_LABEL_MISSING": _NODE + "every outgoing Condition edge needs a label",
    "CONDITION_LABEL_DUPLICATE": _NODE + "duplicate labels",
    "JOIN_FEW_INPUTS": "Join node {node}: needs at least two incoming edges (the branches it waits for)",
    "JOIN_AFTER_CONDITION": "Join node {node}: a Condition cannot feed a Join directly (the Join would wait for a branch that may never run)",
    "RETRIEVER_KB_MISSING": "Retriever node {node}: choose a knowledge base",
    "RETRIEVER_TOP_K": "Retriever node {node}: top_k must be 1-20",
    "MCP_SERVER_MISSING": "MCP node {node}: choose a server",
    "MCP_TOOL_MISSING": "MCP node {node}: choose a tool",
    "MCP_ARGUMENTS": "MCP node {node}: arguments must be an object",
    "HUMAN_ANSWERED_BY": _HUMAN + "answered by must be visitor or reviewer",
    # Code nodes on this server
    "CODE_OFF_DEMO": "Code nodes are turned off in the public demo",
    "CODE_OFF": "Code nodes are turned off on this server (set STUDIO_ENABLE_CODE_NODES=1)",
    "CODE_UNAVAILABLE": "Code nodes cannot run on this server: {reason}",
    "CODE_LANGUAGE_UNAVAILABLE": "{language} Code nodes cannot run on this server: {reason}",
    # Subgraph
    "SUBGRAPH_WORKFLOW_MISSING": _SUBGRAPH + "choose a workflow",
    "SUBGRAPH_CYCLE": _SUBGRAPH + "workflow {workflow} is already in this chain ({chain}), cycles are not allowed",
    "SUBGRAPH_TOO_DEEP": _SUBGRAPH + "subgraphs are nested deeper than {max} levels",
    "SUBGRAPH_NOT_FOUND": _SUBGRAPH + "workflow {workflow} was not found",
    "SUBGRAPH_IMPORTED": _SUBGRAPH + "imported (code) workflows cannot be used as subgraphs",
    "SUBGRAPH_FIELD_TYPE": _SUBGRAPH + "state field {field} is {child_type} in the subgraph but {parent_type} here",
    "SUBGRAPH_START_END": _SUBGRAPH + "workflow {workflow} needs a Start and an End node",
    # Human deadlines (also an Agent node's tool approvals)
    "DEADLINE_NOT_OBJECT": _HUMAN + "deadline must be an object",
    "DEADLINE_DURATION": _HUMAN + "deadline must be a duration like 30m, 4h or 2d",
    "DEADLINE_REMINDER_DURATION": _HUMAN + "reminder interval must be a duration like 30m, 4h or 2d",
    "DEADLINE_REMINDER_OFTEN": _HUMAN + "reminders must come more often than the deadline",
    "DEADLINE_ACTION": _HUMAN + "on timeout must be one of {actions}",
    "DEADLINE_ESCALATE_MISSING": _HUMAN + "add who to escalate to",
    "DEADLINE_ESCALATE_EMAILS": _HUMAN + "escalate to needs e-mail addresses",
    "DEADLINE_TOO_LONG": _HUMAN + "the deadline is longer than the wait limit (STUDIO_WAIT_TTL, {hours} h)",
    # AI review of approvals (TASK-0186)
    "AUTO_APPROVAL_MODE": "Node {node}: AI review mode must be one of {modes}",
    "AUTO_APPROVAL_RULE_INVALID": "Node {node}: AI review rule {index} is not valid (field, operator, value and effect)",
    "AUTO_APPROVAL_JUDGE_REQUIRED": "Node {node}: AI review needs a model credential",
    "AUTO_APPROVAL_CONFIDENCE": "Node {node}: the minimum confidence must be between 0 and 1",
    "AUTO_APPROVAL_CAP": "Node {node}: the daily limit must be a whole number from 1 to {max}",
    # Agent
    "AGENT_PROMPT_MISSING": "Agent node {node}: the task prompt is missing",
    "AGENT_ROUNDS": "Agent node {node}: max rounds must be 1-{max}",
    "AGENT_FIELD_UNKNOWN": "Agent node {node}: {key} '{field}' is not in the state",
    "AGENT_FIELD_NOT_LIST": "Agent node {node}: {key} '{field}' must be a list field",
    "ATTACHMENTS_FIELD_UNKNOWN": "Node {node}: the attachments field '{field}' is not in the state",
    "ATTACHMENTS_FIELD_NOT_LIST": "Node {node}: the attachments field '{field}' must be a list field",
    "AGENT_TOOLS_MISSING": "Agent node {node}: add at least one tool",
    "AGENT_TOOL_NOT_OBJECT": "Agent node {node}: tool {index} is not an object",
    "AGENT_TOOL_DUPLICATE": "Agent node {node}: two tools are named {tool}",
    "AGENT_TOOL_NAME": _AGENT_TOOL + "the name must be 1-64 letters, digits, _ or -",
    "AGENT_TOOL_SOURCE": _AGENT_TOOL + "unknown source '{source}'",
    "AGENT_TOOL_MCP": _AGENT_TOOL + "choose an MCP server and tool",
    "AGENT_TOOL_FUNCTION": _AGENT_TOOL + "function '{function}' is not registered",
    "AGENT_TOOL_KB": _AGENT_TOOL + "choose a knowledge base",
    "AGENT_TOOL_TOP_K": _AGENT_TOOL + "top_k must be 1-20",
    "AGENT_TOOL_URL": _AGENT_TOOL + "URL is missing",
    "AGENT_TOOL_METHOD": _AGENT_TOOL + "method must be one of {methods}",
    "AGENT_TOOL_PARAMETERS": _AGENT_TOOL + "parameters must be a JSON Schema object with properties",
    "AGENT_TOOL_WORKFLOW": _AGENT_TOOL + "choose a workflow",
    "AGENT_TOOL_INPUTS": _AGENT_TOOL + "the parameter fields must be different state field names",
    "AGENT_TOOL_OUTPUTS": _AGENT_TOOL + "choose one or more different state fields as the result",
    "WORKFLOW_TOOL_NOT_FOUND": _AGENT_TOOL + "workflow {workflow} was not found",
    "WORKFLOW_TOOL_CYCLE": _AGENT_TOOL + "workflow {workflow} is already in this chain ({chain}), cycles are not allowed",
    "WORKFLOW_TOOL_TOO_DEEP": _AGENT_TOOL + "workflow tools and subgraphs are nested deeper than {max} levels",
    "WORKFLOW_TOOL_IMPORTED": _AGENT_TOOL + "imported (code) workflows cannot be used as tools",
    "WORKFLOW_TOOL_INPUT_UNKNOWN": _AGENT_TOOL + "parameter field {field} is not in the workflow's state",
    "WORKFLOW_TOOL_OUTPUT_UNKNOWN": _AGENT_TOOL + "result field {field} is not in the workflow's state",
    # Decision
    "DECISION_QUESTIONS_MISSING": _DECISION + "add at least one question",
    "DECISION_QUESTIONS_MANY": _DECISION + "at most {max} questions",
    "DECISION_TEXT_EMPTY": _DECISION + "the text to evaluate is empty",
    "DECISION_QUESTION_NOT_OBJECT": _DECISION + "question {index} is not an object",
    "DECISION_QUESTION_DUPLICATE": _DECISION + "duplicate question id '{question}'",
    "DECISION_OUTPUT_UNKNOWN": _DECISION + "output_field '{field}' is not in the state",
    "DECISION_OUTPUT_TYPE": _DECISION + "output_field '{field}' must be of type object",
    "DECISION_FIELDS_MISSING": _DECISION + "choose an output field or a field for at least one question",
    "DECISION_QUESTION_ID": _QUESTION + "the id must start with a letter or _ and use letters, digits and _",
    "DECISION_QUESTION_TYPE": _QUESTION + "type must be one of {types}",
    "DECISION_INSTRUCTIONS_EMPTY": _QUESTION + "instructions are empty",
    "DECISION_OPTIONS_COUNT": _QUESTION + "needs {min}-{max} options",
    "DECISION_OPTION_LABEL": _QUESTION + "every option needs a label",
    "DECISION_OPTION_LABELS_SAME": _QUESTION + "option labels must be different",
    "DECISION_LEVELS_COUNT": _QUESTION + "needs {min}-{max} levels",
    "DECISION_LEVEL_EMPTY": _QUESTION + "every level needs a description",
    "DECISION_FIELD_UNKNOWN": _QUESTION + "field '{field}' is not in the state",
    "DECISION_FIELD_TYPE": _QUESTION + "field '{field}' must be of type {types}",
    "DECISION_FIELD_REDUCER": _QUESTION + "field '{field}' must not have a reducer",
    # Send email
    "EMAIL_FIELD_TEXT": _EMAIL + "{key} must be text",
    "EMAIL_ADDRESS_INVALID": _EMAIL + "'{address}' in {key} is not an e-mail address",
    "EMAIL_RECIPIENT_MISSING": _EMAIL + "add a recipient (To, Cc or Bcc)",
    "EMAIL_RECIPIENTS_MANY": _EMAIL + "at most {max} recipients",
    "EMAIL_SUBJECT_EMPTY": _EMAIL + "the subject is empty",
    "EMAIL_BODY_EMPTY": _EMAIL + "the message is empty",
    "EMAIL_FORMAT": _EMAIL + "format must be text or html",
    "EMAIL_NO_RETRY": _EMAIL + "retry and cache are not available, an e-mail must be sent once",
    "EMAIL_OUTPUT_UNKNOWN": _EMAIL + "output_field '{field}' is not in the state",
    "EMAIL_OUTPUT_TYPE": _EMAIL + "output_field '{field}' must be of type object",
    # For each
    "FOREACH_LIST_MISSING": _FOREACH + "choose the list field",
    "FOREACH_ITEM_MISSING": _FOREACH + "choose the item field",
    "FOREACH_LIST_UNKNOWN": _FOREACH + "list field '{field}' is not in the state",
    "FOREACH_ITEM_UNKNOWN": _FOREACH + "item field '{field}' is not in the state",
    "FOREACH_INDEX_UNKNOWN": _FOREACH + "index field '{field}' is not in the state",
    "FOREACH_LIST_TYPE": _FOREACH + "list field '{field}' must be of type {types}",
    "FOREACH_INDEX_TYPE": _FOREACH + "index field '{field}' must be of type {types}",
    "FOREACH_ITEM_REDUCER": _FOREACH + "item field '{field}' must not have a reducer (each item replaces the last)",
    "FOREACH_INDEX_REDUCER": _FOREACH + "index field '{field}' must not have a reducer (each item replaces the last)",
    "FOREACH_FIELDS_SAME": _FOREACH + "the list, item and index fields must be different fields",
    "FOREACH_MAX_ITEMS": _FOREACH + "max items must be an integer from {min} to {max}",
    "FOREACH_EDGES": _FOREACH + "needs exactly one '{each}' edge (the loop body) and one '{done}' edge (after the last item)",
    "FOREACH_BODY": _FOREACH + "the '{each}' branch must lead back to this For each node",
    # run input
    "INPUT_NOT_OBJECT": 'Input must be a JSON object, e.g. {{"message": "hi"}}',
    "INPUT_TYPE": "Input '{field}' must be of type {type} (got {got})",
}
MESSAGES.update({f"NODE_{k}": _NODE + text for k, text in CODE_INNER.items()})
MESSAGES.update({f"NODE_REF_{k}": _NODE + text + " in {ref}" for k, text in REF_INNER.items()})


class Issue(str):
    """A validation message: the English text plus its code and parameters (see the module docstring)."""
    code: str
    params: Dict[str, Any]

    def __new__(cls, code: str, text: Optional[str] = None, **params: Any) -> "Issue":
        template = MESSAGES.get(code) or INNER[code]
        self = super().__new__(cls, template.format(**params) if text is None else text)
        self.code, self.params = code, params
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "params": {k: v if isinstance(v, (str, int, float, bool)) else str(v)
                                              for k, v in self.params.items()}}


def at_node(nid: str, problem: str, ref: Optional[str] = None) -> Issue:
    """`problem` (from a node's code or a template reference) as `Node <nid>: problem[ in <ref>]`."""
    extra = {"ref": ref} if ref is not None else {}
    prefix = "NODE_REF_" if ref is not None else "NODE_"
    if isinstance(problem, Issue) and prefix + problem.code in MESSAGES:
        return Issue(prefix + problem.code, node=nid, **extra, **problem.params)
    return Issue(prefix + "PROBLEM", node=nid, detail=str(problem), **extra)


def issues_of(errors: Iterable[str]) -> List[Optional[Dict[str, Any]]]:
    """The codes of `errors`, index by index; None where a message has none (a code checker's own text)."""
    return [e.to_dict() if isinstance(e, Issue) else None for e in errors]
