EXAMPLE = {
  "name": "Customer Support (example)",
  "state": [
    {"name": "message", "type": "string"},
    {"name": "intent", "type": "string"},
    {"name": "tool_result", "type": "string"},
    {"name": "answer", "type": "string"},
  ],
  "nodes": [
    {"id": "start", "type": "start", "position": {"x": 40, "y": 200}, "data": {"label": "Start"}},
    {"id": "classify", "type": "llm", "position": {"x": 240, "y": 200}, "data": {
      "label": "Classify intent", "model": "gpt-4o-mini", "output_field": "intent",
      "prompt": "Classify the customer message into exactly one of: order_status, general. Reply with the label only.\nMessage: {{state.message}}"}},
    {"id": "route", "type": "condition", "position": {"x": 470, "y": 200}, "data": {"label": "Route by intent", "field": "intent", "default": "general"}},
    {"id": "lookup", "type": "tool", "position": {"x": 700, "y": 90}, "data": {"label": "Lookup order", "mode": "function", "function": "lookup_order", "output_field": "tool_result"}},
    {"id": "reply_order", "type": "llm", "position": {"x": 930, "y": 90}, "data": {
      "label": "Reply with order info", "model": "gpt-4o-mini", "output_field": "answer",
      "prompt": "You are a customer support agent. Using the order information, answer the customer briefly.\n{{state.tool_result}}"}},
    {"id": "answer", "type": "llm", "position": {"x": 700, "y": 320}, "data": {
      "label": "General answer", "model": "gpt-4o-mini", "output_field": "answer",
      "prompt": "You are a friendly customer support agent. Answer this question:\n{{state.message}}"}},
    {"id": "end", "type": "end", "position": {"x": 1160, "y": 200}, "data": {"label": "End"}},
  ],
  "edges": [
    {"id": "e1", "source": "start", "target": "classify"},
    {"id": "e2", "source": "classify", "target": "route"},
    {"id": "e3", "source": "route", "target": "lookup", "label": "order_status"},
    {"id": "e4", "source": "route", "target": "answer", "label": "general"},
    {"id": "e5", "source": "lookup", "target": "reply_order"},
    {"id": "e6", "source": "reply_order", "target": "end"},
    {"id": "e7", "source": "answer", "target": "end"},
  ],
}
