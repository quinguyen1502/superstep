"""Python tool registry used by Tool nodes (mode=function)."""
from __future__ import annotations
import os, re, time
from typing import Any, Callable, Dict
from .locale import LOCALES, catalog

TOOLS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
PARAMETERS: Dict[str, Dict[str, Any]] = {}  # name -> JSON Schema of the arguments an Agent node's model fills
NO_PARAMETERS: Dict[str, Any] = {"type": "object", "properties": {}}

def register_tool(name: str, parameters: Dict[str, Any] | None = None):
    """`parameters`: what an Agent node's model may pass; the arguments are merged over the run state the tool reads."""
    def deco(fn):
        TOOLS[name] = fn
        PARAMETERS[name] = parameters or NO_PARAMETERS
        return fn
    return deco

ORDERS = {lang: catalog(lang)["tools"]["orders"] for lang in LOCALES}  # example order statuses per language (app/locales)
ORDER_TEXT = {lang: (catalog(lang)["tools"]["no_order"], catalog(lang)["tools"]["order_label"]) for lang in LOCALES}

LOOKUP_ORDER_PARAMETERS = {"type": "object", "properties": {"message": {"type": "string", "description": "Text that contains the order number, e.g. A100"}},
                           "required": ["message"]}

@register_tool("lookup_order", LOOKUP_ORDER_PARAMETERS)  # one line: the Python export copies the function without its decorator
def lookup_order(state: Dict[str, Any], locale: str = "en") -> str:
    """Example function: find an order id (e.g. A100) in state.message and return status, in `locale` (en, vi)."""
    lang = locale if locale in ORDERS else "en"
    m = re.search(r"\b([A-Z]\d{3})\b", str(state.get("message", "")).upper())
    if not m:
        return ORDER_TEXT[lang][0]
    oid, orders = m.group(1), ORDERS[lang]
    return f"{ORDER_TEXT[lang][1]} {oid}: {orders.get(oid, orders['unknown'])}"

REFUND_TEXT = {lang: (catalog(lang)["tools"]["no_order"], catalog(lang)["tools"]["refund_requested"]) for lang in LOCALES}

REQUEST_REFUND_PARAMETERS = {"type": "object", "properties": {"message": {"type": "string", "description": "Text that contains the order number, e.g. A100"}},
                             "required": ["message"]}

@register_tool("request_refund", REQUEST_REFUND_PARAMETERS)  # one line: the Python export copies the function without its decorator
def request_refund(state: Dict[str, Any], locale: str = "en") -> str:
    """Example function: request a refund for the order id (e.g. A100) in state.message. Nothing is paid."""
    lang = locale if locale in REFUND_TEXT else "en"
    m = re.search(r"\b([A-Z]\d{3})\b", str(state.get("message", "")).upper())
    return REFUND_TEXT[lang][1].format(oid=m.group(1)) if m else REFUND_TEXT[lang][0]

if os.environ.get("STUDIO_ENABLE_DEMO_TOOLS") == "1":
    @register_tool("sleep_demo")
    def sleep_demo(state: Dict[str, Any]) -> str:
        """Demo/testing only (STUDIO_ENABLE_DEMO_TOOLS=1): sleeps 1.5 s, to exercise cancel/timeout."""
        time.sleep(1.5); return "slept 1.5s"
