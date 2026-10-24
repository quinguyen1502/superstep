"""Python tool registry used by Tool nodes (mode=function)."""
from __future__ import annotations
import os, re, time
from typing import Any, Callable, Dict

TOOLS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

def register_tool(name: str):
    def deco(fn):
        TOOLS[name] = fn
        return fn
    return deco

ORDERS = {"en": {"A100": "Delivered on 2026-10-10", "B200": "In transit, expected 2026-10-18", "C300": "Processing",
                  "unknown": "not in our system"},
          "vi": {"A100": "Đã giao hàng (delivered) ngày 2026-10-10", "B200": "Đang vận chuyển (in transit), dự kiến 2026-10-18",
                 "C300": "Đang xử lý (processing)", "unknown": "không tồn tại trong hệ thống"}}
ORDER_TEXT = {"en": ("No order number found in the message.", "Order"), "vi": ("Không tìm thấy mã đơn hàng trong tin nhắn.", "Đơn")}

@register_tool("lookup_order")
def lookup_order(state: Dict[str, Any], locale: str = "en") -> str:
    """Example function: find an order id (e.g. A100) in state.message and return status, in `locale` (en, vi)."""
    lang = locale if locale in ORDERS else "en"
    m = re.search(r"\b([A-Z]\d{3})\b", str(state.get("message", "")).upper())
    if not m:
        return ORDER_TEXT[lang][0]
    oid, orders = m.group(1), ORDERS[lang]
    return f"{ORDER_TEXT[lang][1]} {oid}: {orders.get(oid, orders['unknown'])}"

if os.environ.get("STUDIO_ENABLE_DEMO_TOOLS") == "1":
    @register_tool("sleep_demo")
    def sleep_demo(state: Dict[str, Any]) -> str:
        """Demo/testing only (STUDIO_ENABLE_DEMO_TOOLS=1): sleeps 1.5 s, to exercise cancel/timeout."""
        time.sleep(1.5); return "slept 1.5s"
