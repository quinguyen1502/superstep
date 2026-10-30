"""Chat attachments in model calls (TASK-0176, REQ-0077, DEC-0072 decisions 2 and 5).

An LLM or Agent node with `include_attachments` reads the file records in `attachments_field` (default "files"):
{id, name, type, size, text?, text_cut?, data_url?}. Documents reach the model as labelled text blocks after the
prompt. Images reach it as image parts when the model can see images (`providers.vision`); their bytes are read
through the run's `attachment` port at call time, or from a caller's `data_url` (exports), so they never enter the run
state. A model that cannot see gets a note instead, and the run goes on. Nodes without the setting get nothing.
"""
from __future__ import annotations
import base64
from typing import Any, Callable, Dict, List, Optional, Tuple
from .issues import Issue

DEFAULT_FIELD = "files"
NOTE = "An image named {name} was attached, but this model cannot see images."
Load = Callable[[str], Optional[Tuple[str, bytes]]]  # attachment id -> (MIME, bytes), or None


def field_of(d: Dict[str, Any]) -> Optional[str]:
    """The state field a node reads its files from, or None when the node does not include attachments."""
    return (d.get("attachments_field") or DEFAULT_FIELD) if d.get("include_attachments") else None


def errors(nid: str, d: Dict[str, Any], schema: List[Dict[str, Any]]) -> List[str]:
    """The node's attachments field must be a list field of the state (LLM and Agent nodes)."""
    f = field_of(d)
    types = {x["name"]: x.get("type", "string") for x in schema if isinstance(x, dict) and "name" in x}
    if not f or not types: return []
    if f not in types: return [Issue("ATTACHMENTS_FIELD_UNKNOWN", node=nid, field=f)]
    return [] if types[f] == "list" else [Issue("ATTACHMENTS_FIELD_NOT_LIST", node=nid, field=f)]


def records(state: Dict[str, Any], d: Dict[str, Any]) -> List[Dict[str, Any]]:
    f = field_of(d)
    v = state.get(f) if f else None
    return [x for x in v if isinstance(x, dict) and isinstance(x.get("name"), str)] if isinstance(v, list) else []


def is_image(r: Dict[str, Any]) -> bool: return str(r.get("type") or "").startswith("image/")


def documents_text(files: List[Dict[str, Any]]) -> str:
    """The documents as labelled blocks, to append after the prompt."""
    out = []
    for r in files:
        if is_image(r): continue
        text = r.get("text") or ""
        cut = " (cut)" if r.get("text_cut") else ""
        out.append(f'Attached document "{r["name"]}"{cut}:\n{text}' if text else f'Attached document "{r["name"]}" has no text.')
    return "\n\n".join(out)


def image_data(r: Dict[str, Any], load: Optional[Load]) -> Optional[Tuple[str, str]]:
    """(MIME, base64) of an image record: the caller's data_url, else the bytes through the port."""
    url = r.get("data_url")
    if isinstance(url, str) and url.startswith("data:") and ";base64," in url:
        head, data = url.split(",", 1)
        return head[5:].split(";", 1)[0] or str(r.get("type") or "image/png"), data
    got = load(str(r.get("id") or "")) if load and r.get("id") else None
    return (got[0], base64.b64encode(got[1]).decode()) if got else None


def build(prompt: str, files: List[Dict[str, Any]], vision: bool, load: Optional[Load]) -> Tuple[str, List[Dict[str, str]]]:
    """(text, images [{name, mime, data}]) for one user message: the prompt, the document blocks, and a note for each
    image the model cannot get (no vision, or no bytes)."""
    parts, images, notes = [prompt], [], []
    docs = documents_text(files)
    if docs: parts.append(docs)
    for r in files:
        if not is_image(r): continue
        got = image_data(r, load) if vision else None
        if got: images.append({"name": r["name"], "mime": got[0], "data": got[1]})
        else: notes.append(NOTE.format(name=r["name"]))
    if notes: parts.append("\n".join(notes))
    return "\n\n".join(p for p in parts if p), images


def summary(files: List[Dict[str, Any]], locale: str = "en") -> str:
    """What the offline mock says it received: each file's kind and name."""
    words = {"en": ("Attachments", "image", "document"), "vi": ("Tệp đính kèm", "ảnh", "tài liệu")}
    head, img, doc = words.get(locale, words["en"])
    return f"{head}: " + ", ".join(f"{img if is_image(r) else doc} {r['name']}" for r in files)
