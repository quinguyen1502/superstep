"""Connected Dataset adapters embedded in the generated projects."""

PY_DATASET = r'''
# --- Dataset bindings -------------------------------------------------------------------------------------------
def dataset_operation_id(config: RunnableConfig) -> str:
    namespace = (config.get("metadata") or {}).get("langgraph_checkpoint_ns")
    return hashlib.sha256(namespace.encode()).hexdigest() if isinstance(namespace, str) and namespace else uuid.uuid4().hex


def dataset_call(binding: str, operation: str, fields: list[str], arguments: dict, operation_id: str | None = None) -> dict:
    if binding not in DATASET_BINDINGS:
        raise RuntimeError("DATASET_BINDING_MISSING: configure the Dataset in Studio before exporting")
    backend = dataset_backend(binding)
    if backend != "superstep":
        return dataset_standalone(binding, backend, operation, fields, arguments, operation_id)
    address, token, dataset_id = (os.getenv(f"{binding}_{suffix}") for suffix in ("API_URL", "API_TOKEN", "ID"))
    if not address or not token or not dataset_id:
        raise RuntimeError(f"DATASET_BINDING_MISSING: set {binding}_API_URL, {binding}_API_TOKEN and {binding}_ID")
    try:
        base = httpx.URL(address)
    except (httpx.InvalidURL, ValueError):
        raise RuntimeError(f"DATASET_BINDING_INVALID: invalid {binding}_API_URL") from None
    if (base.scheme not in ("http", "https") or not base.host or base.userinfo or base.query or base.fragment
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", dataset_id)):
        raise RuntimeError(f"DATASET_BINDING_INVALID: check {binding}_API_URL and {binding}_ID")
    url = str(base).rstrip("/") + "/api/datasets/" + dataset_id + "/connected"
    request = {"version": 1, "operation": operation, "columns": DATASET_BINDINGS[binding]["columns"],
               "fields": fields, "arguments": arguments}
    if operation_id is not None:
        request["operation_id"] = operation_id
    with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
        for attempt in range(2):
            try:
                with client.stream("POST", url, json=request, headers={"Authorization": f"Bearer {token}"}) as response:
                    if response.status_code in (502, 503, 504) and attempt == 0:
                        continue
                    if response.is_redirect:
                        raise RuntimeError("DATASET_TRANSPORT_ERROR: the server returned a redirect")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        if len(body) + len(chunk) > 2_097_152:
                            raise RuntimeError("DATASET_TRANSPORT_ERROR: response exceeded 2 MiB")
                        body.extend(chunk)
                    try:
                        payload = json.loads(body)
                    except ValueError:
                        raise RuntimeError(f"DATASET_TRANSPORT_ERROR: HTTP {response.status_code}") from None
                    if response.is_success and isinstance(payload, dict) and payload.get("success") is True and isinstance(payload.get("data"), dict):
                        return payload["data"]
                    error = (payload.get("error") or {}) if isinstance(payload, dict) else {}
                    code = error.get("code") if isinstance(error, dict) else None
                    if isinstance(code, str) and re.fullmatch(r"[A-Z0-9_]{1,80}", code):
                        raise RuntimeError(f"{code}: the connected Dataset rejected {operation}")
                    raise RuntimeError(f"DATASET_TRANSPORT_ERROR: HTTP {response.status_code}")
            except (httpx.TransportError, httpx.DecodingError):
                if attempt:
                    raise RuntimeError("DATASET_TRANSPORT_ERROR: could not reach the connected Dataset") from None
    raise RuntimeError("DATASET_TRANSPORT_ERROR: could not reach the connected Dataset")


def dataset_agent(binding: str, fields: list[str], allowed: dict, limit: int, args: dict) -> dict:
    if not isinstance(args, dict) or args.keys() - {"filters"}:
        raise ValueError("DATASET_NODE_ARGUMENTS_INVALID")
    filters = args.get("filters", [])
    if not isinstance(filters, list) or len(filters) > 12:
        raise ValueError("DATASET_NODE_ARGUMENTS_INVALID")
    for rule in filters:
        if (not isinstance(rule, dict) or not isinstance(rule.get("field"), str)
                or rule.get("op") not in allowed.get(rule["field"], [])):
            raise ValueError("DATASET_FILTER_INVALID")
    page = dataset_call(binding, "find_rows", fields, {"filters": filters, "limit": limit})
    rows, length = [], 0
    for item in page["items"]:
        length += len(json.dumps(item["values"], ensure_ascii=False)) + 2
        if length > 7950:
            break
        rows.append(item["values"])
    return {"rows": rows, "truncated": len(rows) < len(page["items"]) or page["next_offset"] is not None}
'''

TS_DATASET = r'''
// --- Dataset bindings ---------------------------------------------------------------------------------------
async function datasetOperationId(config: unknown): Promise<string> {
  const runtime = config as { executionInfo?: { taskId?: string }; metadata?: Record<string, unknown> } | undefined;
  const namespace = runtime?.executionInfo?.taskId ?? runtime?.metadata?.langgraph_checkpoint_ns;
  if (typeof namespace !== "string" || !namespace) return crypto.randomUUID();
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(namespace));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function datasetCall(binding: string, operation: string, fields: string[], args: Record<string, unknown>, operationId?: string) {
  const contract = DATASET_BINDINGS[binding];
  if (!contract) throw new Error("DATASET_BINDING_MISSING: configure the Dataset in Studio before exporting");
  const backend = env(binding + "_BACKEND");
  if (!backend) throw new Error(`DATASET_BINDING_MISSING: setting=${binding}_BACKEND, choices=superstep, sqlite, postgresql`);
  if (backend !== "superstep") {
    if (backend !== "sqlite" && backend !== "postgresql") {
      throw new Error(`DATASET_BINDING_INVALID: setting=${binding}_BACKEND, choices=superstep, sqlite, postgresql`);
    }
    return await datasetStandalone(binding, backend, operation, fields, args, operationId);
  }
  const address = env(binding + "_API_URL"), token = env(binding + "_API_TOKEN"), id = env(binding + "_ID");
  if (!address || !token || !id) throw new Error(`DATASET_BINDING_MISSING: set ${binding}_API_URL, ${binding}_API_TOKEN and ${binding}_ID`);
  let base: URL;
  try { base = new URL(address); }
  catch { throw new Error(`DATASET_BINDING_INVALID: invalid ${binding}_API_URL`); }
  if (!["http:", "https:"].includes(base.protocol) || base.username || base.password || base.search || base.hash || !/^[A-Za-z0-9_-]{1,100}$/.test(id)) {
    throw new Error(`DATASET_BINDING_INVALID: check ${binding}_API_URL and ${binding}_ID`);
  }
  const url = base.href.replace(/\/+$/, "") + "/api/datasets/" + id + "/connected";
  const body = JSON.stringify({ version: 1, operation, columns: contract.columns, fields, arguments: args,
    ...(operationId === undefined ? {} : { operation_id: operationId }) });
  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
  for (let attempt = 0; attempt < 2; attempt++) {
    let response: Response;
    let text = "";
    try {
      response = await fetch(url, { method: "POST", headers, body, redirect: "manual", signal: AbortSignal.timeout(15000) });
      if (attempt === 0 && [502, 503, 504].includes(response.status)) {
        await response.body?.cancel();
        continue;
      }
      const reader = response.body?.getReader();
      if (reader) {
        const decoder = new TextDecoder();
        let bytes = 0;
        while (true) {
          const chunk = await reader.read();
          if (chunk.done) break;
          bytes += chunk.value.byteLength;
          if (bytes > 2_097_152) {
            await reader.cancel();
            throw new RangeError("DATASET_TRANSPORT_ERROR: response exceeded 2 MiB");
          }
          text += decoder.decode(chunk.value, { stream: true });
        }
        text += decoder.decode();
      }
    } catch (error) {
      if (error instanceof RangeError) throw error;
      if (attempt === 0) continue;
      throw new Error("DATASET_TRANSPORT_ERROR: could not reach the connected Dataset");
    }
    if (response.type === "opaqueredirect" || (response.status >= 300 && response.status < 400)) {
      throw new Error("DATASET_TRANSPORT_ERROR: the server returned a redirect");
    }
    let payload: { success?: boolean; data?: Record<string, unknown>; error?: { code?: string } } | null = null;
    try { payload = JSON.parse(text); } catch { /* generic HTTP error below */ }
    if (response.ok && payload?.success === true && payload.data && typeof payload.data === "object") return payload.data;
    const code = payload?.error?.code;
    if (typeof code === "string" && /^[A-Z0-9_]{1,80}$/.test(code)) throw new Error(`${code}: the connected Dataset rejected ${operation}`);
    throw new Error(`DATASET_TRANSPORT_ERROR: HTTP ${response.status}`);
  }
  throw new Error("DATASET_TRANSPORT_ERROR: could not reach the connected Dataset");
}

async function datasetAgent(binding: string, fields: string[], allowed: Record<string, string[]>, limit: number, args: Record<string, unknown>) {
  if (!args || Array.isArray(args) || Object.keys(args).some((key) => key !== "filters")) throw new Error("DATASET_NODE_ARGUMENTS_INVALID");
  const filters = Object.hasOwn(args, "filters") ? args.filters : [];
  if (!Array.isArray(filters) || filters.length > 12) throw new Error("DATASET_NODE_ARGUMENTS_INVALID");
  for (const rule of filters) {
    if (!rule || typeof rule.field !== "string" || !Object.hasOwn(allowed, rule.field) || !allowed[rule.field].includes(rule.op)) {
      throw new Error("DATASET_FILTER_INVALID");
    }
  }
  const page = await datasetCall(binding, "find_rows", fields, { filters, limit });
  const items = page.items as { values: Record<string, unknown> }[];
  const rows = [];
  let length = 0;
  for (const item of items) {
    length += JSON.stringify(item.values).length + 2;
    if (length > 7950) break;
    rows.push(item.values);
  }
  return { rows, truncated: rows.length < items.length || page.next_offset !== null };
}
'''
