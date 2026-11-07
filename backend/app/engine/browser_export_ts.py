"""Standalone TypeScript browser runtime embedded in LangGraph.js exports.

Generated files import nothing from Superstep. The string is inserted after
``const BROWSER_POLICY``. ``__LANGGRAPH_SPEC__`` is replaced with the quoted
LangGraph.js specifier at emit time.
"""

TS_RUNTIME = r'''
// Secrets are read from the environment at run time. BROWSER_POLICY has no tokens, passwords or cookies.
const MUTATING = new Set(["click", "fill", "upload", "download", "evaluate"]);
const OBSERVED = new Set(["click", "fill", "extract", "upload", "download", "evaluate"]);
const sessions = new Map<string, Session>();

class BrowserError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = "BrowserError";
    this.code = code;
  }
}

class SessionLost extends BrowserError {
  constructor(message = "session lost") {
    super("session_lost", message);
    this.name = "SessionLost";
  }
}

class UnknownEffect extends BrowserError {
  constructor(message = "unknown effect") {
    super("unknown_effect", message);
    this.name = "UnknownEffect";
  }
}

class Page {
  url = "";
  html = "";
  generation = 0;
  observation: string | null = null;
  elements: Array<{ element_id: string; role: string; text: string; tag: string; href: string }> = [];
  values: Record<string, unknown> = {};
}

class Session {
  tail: Promise<void> = Promise.resolve();
  seq = 0;
  active = 0;
  peak = 0;
  page = new Page();
  touched = nowSeconds();
  started = this.touched;
  actions = 0;
  browser: PwBrowser | null = null;
  context: PwContext | null = null;
  live: PwPage | null = null;
  navError: BrowserError | null = null;
  documents = 0;

  async exclusive<T>(fn: () => Promise<T>): Promise<T> {
    const previous = this.tail;
    let release: () => void = () => {};
    this.tail = new Promise((resolve) => { release = resolve; });
    await previous;
    this.active += 1;
    this.peak = Math.max(this.peak, this.active);
    try {
      return await fn();
    } finally {
      this.active -= 1;
      this.touched = nowSeconds();
      release();
    }
  }
}

function nowSeconds(): number {
  return Date.now() / 1000;
}

function envGet(name: string): string {
  if (!name) return "";
  const fromProcess = typeof process !== "undefined" && process.env ? process.env[name] : undefined;
  if (fromProcess) return fromProcess;
  const deno = (globalThis as { Deno?: { env?: { get(name: string): string | undefined } } }).Deno;
  return deno?.env?.get(name) || "";
}

function envPop(name: string): void {
  if (typeof process !== "undefined" && process.env) delete process.env[name];
  const deno = (globalThis as { Deno?: { env?: { delete?(name: string): void } } }).Deno;
  try { deno?.env?.delete?.(name); } catch { /* Deno without --allow-env */ }
}

function driverName(): string {
  return (envGet("SUPERSTEP_BROWSER_DRIVER") || "memory").trim().toLowerCase();
}

function takeFault(): string {
  const value = envGet("SUPERSTEP_BROWSER_FAULT") || "";
  if (value) envPop("SUPERSTEP_BROWSER_FAULT");
  return value.trim().toLowerCase();
}

function approved(answer: unknown): boolean {
  if (answer === true) return true;
  return !!answer && typeof answer === "object" && (answer as { approved?: unknown }).approved === true;
}

function publicArgs(args: Record<string, unknown> | null): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(args || {})) {
    if (key === "value" || key === "script" || key === "expression" || key === "source_id") out[key] = "[redacted]";
    else if (key === "url" && typeof value === "string") {
      try {
        const parts = new URL(value);
        out[key] = `${parts.protocol}//${parts.hostname || ""}`;
      } catch {
        out[key] = "";
      }
    } else out[key] = value;
  }
  return out;
}

async function browserInterrupt(alias: string, tool: string, args: Record<string, unknown>): Promise<boolean> {
  const loaded = await import(__LANGGRAPH_SPEC__);
  const answer = await loaded.interrupt({ browser: alias, tool, arguments: publicArgs(args) });
  return approved(answer);
}

let browserDecide = async (alias: string, tool: string, args: Record<string, unknown>): Promise<unknown> => {
  return browserInterrupt(alias, tool, args);
};

function bindBrowserUrl(binding: { source?: string; value?: string } | null, args: Record<string, unknown> | null, state: object): Record<string, unknown> {
  const arguments_ = args && typeof args === "object" ? { ...args } : {};
  const source = (binding && binding.source) || "model";
  if (source === "model") return arguments_;
  if ("url" in arguments_) throw new BrowserError("override", "A bound URL cannot be overridden by model arguments");
  let value = "";
  if (source === "fixed") value = (binding && binding.value) || "";
  else if (source === "state") value = render(String((binding && binding.value) || ""), state);
  else return arguments_;
  if (!value.trim()) throw new BrowserError("missing_url", "Bound URL is missing");
  return { ...arguments_, url: value };
}

function selectTarget(target: Record<string, unknown> | null, state: object): [string, string] {
  const field = String((target && target.observation_field) || "");
  const result = (state as Record<string, unknown>)[field];
  if (!result || typeof result !== "object" || (result as { status?: unknown }).status !== "confirmed") {
    throw new BrowserError("missing_target", "Browser recipe target is missing or ambiguous");
  }
  const observation = (result as { observation?: { observation_id?: string; elements?: Array<{ role?: string; text?: string; element_id?: string }> } }).observation || {};
  const elements = observation.elements || [];
  const role = target ? target.role : undefined;
  const text = target ? target.text : undefined;
  const matches = elements.filter((item) => item.role === role && (text === undefined || text === null || item.text === text));
  if (matches.length !== 1 || !observation.observation_id) {
    throw new BrowserError("missing_target", "Browser recipe target is missing or ambiguous");
  }
  return [observation.observation_id, String(matches[0].element_id || "")];
}

function browserPrepare(tool: string, args: Record<string, unknown> | null, target: Record<string, unknown> | null, targets: Record<string, Record<string, unknown>> | null, state: object): Record<string, unknown> {
  const arguments_ = { ...(args || {}) };
  if ((tool === "click" || tool === "fill") && target && typeof target === "object") {
    const [observation, element] = selectTarget(target, state);
    arguments_.observation_id = observation;
    arguments_.element_id = element;
  } else if (tool === "extract" && targets && typeof targets === "object") {
    const fields: Record<string, string> = {};
    let observation: string | null = null;
    for (const [name, item] of Object.entries(targets)) {
      const [current, element] = selectTarget(item, state);
      if (observation !== null && observation !== current) throw new BrowserError("stale_observation", "Browser recipe observation changed");
      observation = current;
      fields[name] = element;
    }
    arguments_.observation_id = observation;
    arguments_.fields = fields;
  }
  return arguments_;
}

function policyFor(alias: string): Record<string, unknown> {
  const table = BROWSER_POLICY as Record<string, Record<string, unknown>>;
  const item = table ? table[alias] : undefined;
  if (!item || typeof item !== "object") throw new BrowserError("missing_policy", "No browser policy for this alias");
  return item;
}

function originOf(url: string): string {
  let parts: URL;
  try { parts = new URL(url); } catch { throw new BrowserError("whitelist_denied", "URL scheme or userinfo is not allowed"); }
  const scheme = parts.protocol === "https:" ? "https" : parts.protocol === "http:" ? "http" : "";
  if (!scheme || !parts.hostname || parts.username || parts.password) {
    throw new BrowserError("whitelist_denied", "URL scheme or userinfo is not allowed");
  }
  const port = parts.port ? Number(parts.port) : (scheme === "https" ? 443 : 80);
  const host = parts.hostname.toLowerCase().replace(/\.$/, "");
  const bracket = host.includes(":") ? `[${host}]` : host;
  const suffix = (scheme === "http" && port === 80) || (scheme === "https" && port === 443) ? "" : `:${port}`;
  return `${scheme}://${bracket}${suffix}`;
}

function allowedOrigin(policy: Record<string, unknown>, url: string): string {
  const origin = originOf(url);
  const allowed: string[] = [];
  for (const item of (policy.allowed_origins as unknown[]) || []) {
    try { allowed.push(originOf(String(item))); } catch { /* skip a stored origin that is not an http(s) URL */ }
  }
  if (!allowed.includes(origin)) throw new BrowserError("whitelist_denied", "URL origin is not on the whitelist");
  return origin;
}

function privateHost(host: string): boolean {
  if (!host || host.toLowerCase() === "localhost") return true;
  const ipv4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(host);
  if (ipv4) {
    const a = Number(ipv4[1]);
    const b = Number(ipv4[2]);
    if (a === 0 || a === 10 || a === 127 || a >= 224) return true;
    if (a === 169 && b === 254) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    if (a === 192 && (b === 168 || b === 0)) return true;
    if (a === 100 && b >= 64 && b <= 127) return true;
    if (a === 198 && (b === 18 || b === 19)) return true;
    if (a === 203 && b === 0) return true;
    return false;
  }
  const lower = host.toLowerCase();
  if (lower === "::1" || lower === "::") return true;
  if (lower.startsWith("fe80:") || lower.startsWith("fc") || lower.startsWith("fd")) return true;
  return false;
}

function requirePublic(url: string): void {
  let host = "";
  try { host = new URL(url).hostname || ""; } catch { host = ""; }
  if (privateHost(host)) throw new BrowserError("private_address", "Playwright and Browserless refuse non-global addresses");
}

function checkSecrets(policy: Record<string, unknown>): void {
  const env = (policy.env || {}) as Record<string, string>;
  if (policy.provider === "browserless") {
    if (!envGet(env.endpoint) || !envGet(env.token)) {
      throw new BrowserError("token_missing", "Browserless endpoint and token must be set in the environment");
    }
  }
  const proxy = (policy.proxy || {}) as Record<string, string>;
  if (proxy.mode === "custom" && proxy.auth === "basic") {
    if (!envGet(env.proxy_username) || !envGet(env.proxy_password)) {
      throw new BrowserError("proxy_credentials_missing", "Proxy username and password must be set in the environment");
    }
  }
  if (policy.profile && !envGet(env.profile)) {
    throw new BrowserError("profile_missing", "profile state is not in the export; set " + String(env.profile || "SUPERSTEP_BROWSER_PROFILE"));
  }
}

function attr(attrs: string, name: string): string {
  for (const quote of ['"', "'"]) {
    const pattern = "\\b" + name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*=\\s*" + quote + "([^" + quote + "]*)" + quote;
    const match = new RegExp(pattern, "i").exec(attrs || "");
    if (match) return match[1];
  }
  return "";
}

function clean(text: string): string {
  return (text || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function roleOf(tag: string, attrs: string): string {
  if (tag === "a") return "link";
  if (tag === "button") return "button";
  if (tag === "input") {
    const kind = (attr(attrs, "type") || "text").toLowerCase();
    return kind === "submit" || kind === "button" ? "button" : "textbox";
  }
  if (tag === "textarea") return "textbox";
  if (tag === "h1") return "heading";
  return "paragraph";
}

function labelOf(tag: string, attrs: string, inner: string): string {
  if (tag === "input") return attr(attrs, "aria-label") || attr(attrs, "placeholder") || attr(attrs, "value") || "";
  return clean(inner);
}

function elementsOf(html: string): Page["elements"] {
  const specs: Array<[string, RegExp]> = [
    ["a", /<a\b([^>]*)>(.*?)<\/a>/gis],
    ["button", /<button\b([^>]*)>(.*?)<\/button>/gis],
    ["input", /<input\b([^>]*)\/?>/gis],
    ["textarea", /<textarea\b([^>]*)>(.*?)<\/textarea>/gis],
    ["h1", /<h1\b([^>]*)>(.*?)<\/h1>/gis],
    ["p", /<p\b([^>]*)>(.*?)<\/p>/gis],
  ];
  const found: Array<[number, string, string, string, string]> = [];
  for (const [tag, pattern] of specs) {
    for (const match of html.matchAll(pattern)) {
      const attrs = match[1] || "";
      const inner = match[2] || "";
      const role = attr(attrs, "role") || roleOf(tag, attrs);
      found.push([match.index || 0, tag, attrs, role.slice(0, 80), labelOf(tag, attrs, inner).slice(0, 1000)]);
    }
  }
  found.sort((a, b) => a[0] - b[0]);
  return found.map((item, index) => {
    const rawId = attr(item[2], "id");
    const elementId = /^[A-Za-z0-9_.:-]+$/.test(rawId) ? rawId : `e${index + 1}`;
    return { element_id: elementId, role: item[3], text: item[4], tag: item[1], href: attr(item[2], "href") };
  });
}

function titleOf(html: string): string {
  const match = /<title[^>]*>(.*?)<\/title>/is.exec(html || "");
  return match ? clean(match[1]) : "";
}

function bodyText(html: string): string {
  const match = /<body[^>]*>(.*)<\/body>/is.exec(html || "");
  return clean(match ? match[1] : html);
}

function observationOf(page: Page): Record<string, unknown> {
  let origin = "";
  if (page.url) {
    try { origin = originOf(page.url); } catch { origin = ""; }
  }
  return {
    observation_id: page.observation,
    page_generation: page.generation,
    origin,
    text: bodyText(page.html).slice(0, 16000),
    elements: page.elements.map((item) => ({ element_id: item.element_id, role: item.role, text: item.text })),
  };
}

function ok(tool: string, seq: number, extra: Record<string, unknown> = {}): Record<string, unknown> {
  return { status: "confirmed", operation: tool, sequence: seq, ...extra };
}

async function readLimited(response: Response): Promise<string> {
  const reader = response.body ? response.body.getReader() : null;
  if (!reader) return "";
  const chunks: Uint8Array[] = [];
  let total = 0;
  while (total < 200000) {
    const step = await reader.read();
    if (step.done) break;
    chunks.push(step.value);
    total += step.value.length;
  }
  await reader.cancel().catch(() => {});
  const bytes = new Uint8Array(Math.min(total, 200000));
  let offset = 0;
  for (const chunk of chunks) {
    const take = Math.min(chunk.length, bytes.length - offset);
    bytes.set(chunk.subarray(0, take), offset);
    offset += take;
    if (offset >= bytes.length) break;
  }
  return new TextDecoder().decode(bytes);
}

async function httpGet(url: string, policy: Record<string, unknown>): Promise<string> {
  allowedOrigin(policy, url);
  const timeout = Math.max(1, Math.floor(Number(policy.action_timeout_ms || 30000) / 1000));
  let response: Response;
  try {
    response = await fetch(url, {
      redirect: "manual",
      headers: { "User-Agent": "superstep-export-browser" },
      signal: AbortSignal.timeout(timeout * 1000),
    });
  } catch (error) {
    if (error instanceof BrowserError) throw error;
    throw new BrowserError("fetch_failed", "fetch failed");
  }
  if (response.status === 0 || (response.status >= 300 && response.status < 400)) {
    throw new BrowserError("whitelist_denied", "redirect is not followed");
  }
  return readLimited(response);
}

function proxyFor(policy: Record<string, unknown>): { server: string; username?: string; password?: string } | undefined {
  const proxy = (policy.proxy || {}) as Record<string, string>;
  if (proxy.mode !== "custom" || !proxy.server) return undefined;
  if (proxy.auth !== "basic") return { server: proxy.server };
  const env = (policy.env || {}) as Record<string, string>;
  return { server: proxy.server, username: envGet(env.proxy_username), password: envGet(env.proxy_password) };
}

interface PwRoute {
  request: { url?: string | (() => string); resourceType?: string | (() => string); resource_type?: string };
  continue(): Promise<void> | void;
  abort(): Promise<void> | void;
}
interface PwLocator {
  click(options?: { timeout?: number }): Promise<void>;
  fill(value: string, options?: { timeout?: number }): Promise<void>;
}
interface PwPage {
  url?: string | (() => string);
  goto(url: string, options?: { timeout?: number }): Promise<unknown>;
  content(): Promise<string>;
  locator(selector: string): PwLocator;
  evaluate(expression: string): Promise<unknown>;
  goBack(options?: { timeout?: number }): Promise<unknown>;
}
interface PwContext {
  route(pattern: string, handler: (route: PwRoute) => Promise<void> | void): Promise<void> | void;
  newPage(): Promise<PwPage>;
  close(): Promise<void>;
}
interface PwBrowser {
  newContext(options?: { storageState?: object }): Promise<PwContext>;
  close(): Promise<void>;
}

async function loadPlaywright(): Promise<{ chromium: { launch(options: object): Promise<PwBrowser>; connectOverCDP(endpoint: string): Promise<PwBrowser> } }> {
  try {
    return await import("playwright");
  } catch {
    try {
      return await import("npm:" + "playwright");
    } catch {
      throw new BrowserError("capability_refused", "playwright is not installed; install playwright and chromium, or set SUPERSTEP_BROWSER_DRIVER=memory");
    }
  }
}

function callString(target: object | null, value: string | (() => string) | undefined): string {
  if (typeof value === "function") {
    try { return value.call(target) || ""; } catch { return ""; }
  }
  return value || "";
}

function pageUrl(page: PwPage | null): string {
  return page ? callString(page, page.url) : "";
}

function requestResource(request: PwRoute["request"]): string {
  const named = callString(request, request.resourceType);
  return named || request.resource_type || "";
}

async function closeLive(session: Session): Promise<void> {
  const context = session.context;
  const browser = session.browser;
  session.live = null;
  session.context = null;
  session.browser = null;
  session.documents = 0;
  session.navError = null;
  for (const target of [context, browser]) {
    if (!target || typeof target.close !== "function") continue;
    try { await target.close(); } catch { /* already closed */ }
  }
}

let shutdownStarted = false;
async function shutdownLive(): Promise<void> {
  if (shutdownStarted) return;
  shutdownStarted = true;
  for (const session of [...sessions.values()]) await closeLive(session);
}

if (typeof process !== "undefined" && typeof process.on === "function") {
  process.on("beforeExit", () => { void shutdownLive(); });
}

function listedOrigins(policy: Record<string, unknown>): string[] {
  const found: string[] = [];
  const profile = (policy.profile || {}) as { origins?: unknown[] };
  for (const item of profile.origins || []) {
    try { found.push(originOf(String(item))); } catch { /* skip */ }
  }
  return found;
}

function domainMatch(host: string, domain: string): boolean {
  const left = (host || "").toLowerCase().replace(/\.$/, "");
  const right = (domain || "").toLowerCase().replace(/^\./, "").replace(/\.$/, "");
  if (!left || !right) return false;
  return left === right || left.endsWith("." + right);
}

function profileState(policy: Record<string, unknown>): { cookies: object[]; origins: object[] } | null {
  if (!policy.profile) return null;
  const env = (policy.env || {}) as Record<string, string>;
  let data: { cookies?: unknown[]; origins?: unknown[] };
  try {
    const parsed = JSON.parse(envGet(env.profile));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("shape");
    data = parsed as { cookies?: unknown[]; origins?: unknown[] };
  } catch {
    throw new BrowserError("profile_invalid", "profile JSON is invalid");
  }
  const listed = listedOrigins(policy);
  const cookies: object[] = [];
  for (const cookie of data.cookies || []) {
    if (!cookie || typeof cookie !== "object") continue;
    const item = cookie as Record<string, unknown>;
    const name = item.name;
    const value = item.value;
    const domain = item.domain;
    if (typeof name !== "string" || !name || typeof value !== "string" || typeof domain !== "string" || item.secure !== true) continue;
    let matched = false;
    for (const origin of listed) {
      let host = "";
      try { host = new URL(origin).hostname || ""; } catch { host = ""; }
      if (!domainMatch(host, domain) || privateHost(host)) continue;
      try { allowedOrigin(policy, origin); } catch { continue; }
      matched = true;
      break;
    }
    if (!matched) continue;
    const path = typeof item.path === "string" && item.path.startsWith("/") ? item.path : "/";
    const stored: Record<string, unknown> = { name, value, domain, path, httpOnly: Boolean(item.httpOnly), secure: true };
    if (item.sameSite === "Strict" || item.sameSite === "Lax" || item.sameSite === "None") stored.sameSite = item.sameSite;
    if (typeof item.expires === "number" && item.expires >= 0) stored.expires = item.expires;
    cookies.push(stored);
  }
  const origins: object[] = [];
  for (const entry of data.origins || []) {
    if (!entry || typeof entry !== "object") continue;
    const row = entry as { origin?: unknown; localStorage?: unknown[] };
    let origin = "";
    try { origin = originOf(String(row.origin || "")); } catch { continue; }
    let host = "";
    try { host = new URL(origin).hostname || ""; } catch { host = ""; }
    if (!listed.includes(origin) || privateHost(host)) continue;
    try { allowedOrigin(policy, origin); } catch { continue; }
    const stored: Array<{ name: string; value: string }> = [];
    for (const pair of row.localStorage || []) {
      if (pair && typeof pair === "object") {
        const fields = pair as { name?: unknown; value?: unknown };
        if (typeof fields.name === "string" && typeof fields.value === "string") stored.push({ name: fields.name, value: fields.value });
      }
    }
    origins.push({ origin, localStorage: stored });
  }
  return { cookies, origins };
}

async function abandon(browser: PwBrowser | null): Promise<void> {
  if (!browser) return;
  try { await browser.close(); } catch { /* launch failed */ }
}

async function routeLive(session: Session, policy: Record<string, unknown>, route: PwRoute): Promise<void> {
  const url = callString(route.request, route.request.url);
  let scheme = "";
  try { scheme = new URL(url).protocol.replace(":", "").toLowerCase(); } catch { scheme = ""; }
  if (scheme === "about" || scheme === "data" || scheme === "blob") {
    await route.continue();
    return;
  }
  try {
    allowedOrigin(policy, url);
    requirePublic(url);
  } catch (error) {
    if (error instanceof BrowserError && requestResource(route.request) === "document") session.navError = error;
    await route.abort();
    return;
  }
  await route.continue();
}

async function openLive(session: Session, policy: Record<string, unknown>): Promise<void> {
  if (session.live) return;
  const profile = profileState(policy);
  const kind = driverName();
  let loaded: Awaited<ReturnType<typeof loadPlaywright>>;
  try {
    loaded = await loadPlaywright();
  } catch (error) {
    if (kind === "browserless" && error instanceof BrowserError && error.code === "capability_refused") {
      throw new BrowserError("capability_refused", "playwright is required for browserless connect_over_cdp");
    }
    throw error;
  }
  let browser: PwBrowser | null = null;
  try {
    if (kind === "browserless") {
      const env = (policy.env || {}) as Record<string, string>;
      const endpoint = envGet(env.endpoint);
      const token = envGet(env.token);
      if (!endpoint || !token) throw new BrowserError("token_missing", "Browserless endpoint and token must be set in the environment");
      const sep = endpoint.includes("?") ? "&" : "?";
      let target = endpoint + sep + "token=" + token;
      // stealth is a Browserless query only. Local chromium.launch must not receive it.
      if (policy.stealth) target += "&stealth=true";
      browser = await loaded.chromium.connectOverCDP(target);
    } else {
      const options: { headless: boolean; proxy?: object } = { headless: true };
      const proxy = proxyFor(policy);
      if (proxy) options.proxy = proxy;
      browser = await loaded.chromium.launch(options);
    }
    const context = await browser.newContext(profile ? { storageState: profile } : {});
    await context.route("**/*", (route) => routeLive(session, policy, route));
    session.browser = browser;
    session.context = context;
    session.live = await context.newPage();
  } catch (error) {
    await abandon(browser);
    if (error instanceof BrowserError) throw error;
    throw new BrowserError("fetch_failed", "launch failed");
  }
}

async function restoreLive(session: Session, before: string, timeout: number): Promise<void> {
  const page = session.live;
  if (!page || pageUrl(page) === before) return;
  try {
    await page.goBack({ timeout });
  } catch {
    await closeLive(session);
    return;
  }
  if (pageUrl(session.live) !== before) await closeLive(session);
}

async function gotoLive(session: Session, policy: Record<string, unknown>, url: string): Promise<string> {
  await openLive(session, policy);
  const limit = Number(policy.max_pages || 4);
  if (session.documents >= limit) throw new BrowserError("limit", "max_pages reached");
  const page = session.live as PwPage;
  const before = pageUrl(page);
  session.navError = null;
  const timeout = Number(policy.action_timeout_ms || 30000);
  let failed: Error | null = null;
  try {
    await page.goto(url, { timeout });
  } catch (error) {
    failed = error instanceof BrowserError ? error : (session.navError || new BrowserError("fetch_failed", "fetch failed"));
  }
  if (session.navError) failed = session.navError;
  session.navError = null;
  if (failed) {
    await restoreLive(session, before, timeout);
    throw failed;
  }
  session.documents += 1;
  try {
    return await page.content();
  } catch {
    throw new BrowserError("fetch_failed", "fetch failed");
  }
}

async function fetchPage(session: Session, policy: Record<string, unknown>, url: string): Promise<string> {
  // max_pages applies to the live page only. The memory driver stays a static fetch.
  allowedOrigin(policy, url);
  const kind = driverName();
  if (kind === "playwright" || kind === "browserless") {
    requirePublic(url);
    return gotoLive(session, policy, url);
  }
  if (kind !== "memory") throw new BrowserError("capability_refused", "SUPERSTEP_BROWSER_DRIVER must be memory, playwright, or browserless");
  return httpGet(url, policy);
}

function liveLocator(session: Session, elementId: string): PwLocator {
  return (session.live as PwPage).locator("[id=" + JSON.stringify(elementId) + "]");
}

async function liveClick(session: Session, policy: Record<string, unknown>, element: Page["elements"][number]): Promise<Record<string, unknown>> {
  const page = session.live as PwPage;
  const before = pageUrl(page) || session.page.url || "";
  const timeout = Number(policy.action_timeout_ms || 30000);
  session.navError = null;
  let failed: Error | null = null;
  try {
    await liveLocator(session, element.element_id).click({ timeout });
  } catch (error) {
    failed = error instanceof BrowserError ? error : (session.navError || new BrowserError("fetch_failed", "click failed"));
  }
  if (session.navError) failed = session.navError;
  session.navError = null;
  if (failed) {
    await restoreLive(session, before, timeout);
    throw failed;
  }
  const after = pageUrl(session.live) || before;
  if (after !== before) {
    const limit = Number(policy.max_pages || 4);
    if (session.documents >= limit) {
      await restoreLive(session, before, timeout);
      throw new BrowserError("limit", "max_pages reached");
    }
    try {
      allowedOrigin(policy, after);
      requirePublic(after);
    } catch (error) {
      await restoreLive(session, before, timeout);
      throw error;
    }
    session.documents += 1;
  }
  let html = "";
  try {
    html = await (session.live as PwPage).content();
  } catch {
    throw new BrowserError("fetch_failed", "fetch failed");
  }
  return storePage(session, after, html, "click");
}

async function liveFill(session: Session, policy: Record<string, unknown>, element: Page["elements"][number], value: unknown): Promise<Record<string, unknown>> {
  const timeout = Number(policy.action_timeout_ms || 30000);
  session.navError = null;
  const text = typeof value === "string" ? value : "";
  try {
    await liveLocator(session, element.element_id).fill(text, { timeout });
  } catch (error) {
    const failed = error instanceof BrowserError ? error : (session.navError || new BrowserError("fetch_failed", "fill failed"));
    session.navError = null;
    throw failed;
  }
  if (session.navError) {
    const failed = session.navError;
    session.navError = null;
    throw failed;
  }
  const url = pageUrl(session.live) || session.page.url || "";
  try {
    return storePage(session, url, await (session.live as PwPage).content(), "fill");
  } catch {
    throw new BrowserError("fetch_failed", "fetch failed");
  }
}

function storePage(session: Session, url: string, html: string, operation: string): Record<string, unknown> {
  const page = new Page();
  page.url = url;
  page.html = html;
  page.generation = session.page.generation + 1;
  page.elements = elementsOf(html);
  session.page = page;
  session.actions += 1;
  session.seq += 1;
  page.observation = `g${page.generation}-s${session.seq}`;
  return ok(operation, session.seq, { url, observation: observationOf(page) });
}

function fresh(session: Session, args: Record<string, unknown>): void {
  const observation = args.observation_id;
  if (typeof observation !== "string" || observation !== session.page.observation) {
    throw new BrowserError("stale_observation", "observation_id does not match the current page");
  }
}

function elementOf(session: Session, elementId: unknown): Page["elements"][number] {
  for (const item of session.page.elements) {
    if (item.element_id === elementId) return item;
  }
  throw new BrowserError("missing_target", "element_id is not on the current page");
}

async function expire(session: Session, policy: Record<string, unknown>): Promise<void> {
  const now = nowSeconds();
  const life = Number(policy.lifetime_s || 0);
  const idle = Number(policy.idle_timeout_s || 0);
  if (life && now - session.started > life) {
    await closeLive(session);
    session.page = new Page();
    throw new SessionLost("lifetime exceeded");
  }
  if (idle && now - session.touched > idle) {
    await closeLive(session);
    session.page = new Page();
    throw new SessionLost("idle timeout");
  }
}

async function command(session: Session, policy: Record<string, unknown>, alias: string, tool: string, args: Record<string, unknown>): Promise<Record<string, unknown>> {
  await expire(session, policy);
  const fault = takeFault();
  if (fault === "lost") {
    await closeLive(session);
    session.page = new Page();
    throw new SessionLost("injected lost session");
  }
  if (fault === "unknown") throw new UnknownEffect("injected unknown effect");
  if (fault) throw new BrowserError("capability_refused", "SUPERSTEP_BROWSER_FAULT must be empty, lost, or unknown");
  if (MUTATING.has(tool) && policy.require_mutating_approval) {
    if (!approved(await browserDecide(alias, tool, args))) {
      throw new BrowserError("approval_rejected", "mutating browser action was not approved");
    }
  }
  if (session.actions >= Number(policy.max_actions || 1)) throw new BrowserError("limit", "max_actions reached");
  if (OBSERVED.has(tool)) fresh(session, args);
  if (tool === "upload" || tool === "download") {
    const flag = tool === "upload" ? "allow_upload" : "allow_download";
    const allowed = Boolean(policy[flag]);
    throw new BrowserError("capability_refused", `${tool} is refused outside Studio; the connection allow flag is ${allowed} but this runtime has no attachment store`);
  }
  if (tool === "navigate") {
    const url = args.url;
    if (typeof url !== "string" || !url.trim() || url.trim().toLowerCase().startsWith("javascript:")) {
      throw new BrowserError(typeof url === "string" && url.trim() ? "whitelist_denied" : "missing_url", "navigate needs an http(s) url");
    }
    return storePage(session, url.trim(), await fetchPage(session, policy, url.trim()), "navigate");
  }
  if (tool === "snapshot") {
    session.actions += 1;
    session.seq += 1;
    session.page.elements = elementsOf(session.page.html);
    session.page.observation = `g${session.page.generation}-s${session.seq}`;
    return ok("snapshot", session.seq, { observation: observationOf(session.page) });
  }
  if (tool === "screenshot") {
    session.actions += 1;
    session.seq += 1;
    return ok("screenshot", session.seq, { captured: true, inline_bytes: false });
  }
  if (tool === "click") {
    const element = elementOf(session, args.element_id);
    if (element.href) {
      const target = new URL(element.href, session.page.url || undefined).href;
      allowedOrigin(policy, target);
      return storePage(session, target, await fetchPage(session, policy, target), "click");
    }
    if (session.live) return liveClick(session, policy, element);
    session.actions += 1;
    session.seq += 1;
    return ok("click", session.seq, { clicked: element.element_id });
  }
  if (tool === "fill") {
    const element = elementOf(session, args.element_id);
    if (session.live) return liveFill(session, policy, element, args.value);
    session.page.values[element.element_id] = args.value;
    session.actions += 1;
    session.seq += 1;
    return ok("fill", session.seq, { filled: true });
  }
  if (tool === "extract") {
    const fields = args.fields;
    if (!fields || typeof fields !== "object" || Array.isArray(fields) || !Object.keys(fields).length) {
      throw new BrowserError("missing_target", "extract needs fields");
    }
    const extracted: Record<string, string> = {};
    for (const [name, elementId] of Object.entries(fields as Record<string, unknown>)) {
      extracted[name] = elementOf(session, elementId).text || "";
    }
    session.actions += 1;
    session.seq += 1;
    return ok("extract", session.seq, { fields: extracted });
  }
  if (tool === "evaluate") {
    if (!policy.allow_evaluate_js) throw new BrowserError("capability_refused", "evaluate is disabled on this connection");
    const raw = args.expression;
    const expression = typeof raw === "string" ? raw : "";
    let value: unknown = "";
    if (session.live) {
      if (expression.length > 4000) throw new BrowserError("capability_refused", "evaluate expression exceeds 4000 characters");
      try {
        value = await session.live.evaluate(expression);
      } catch (error) {
        if (error instanceof BrowserError) throw error;
        throw new BrowserError("fetch_failed", "evaluate failed");
      }
    } else if (expression === "document.title") value = titleOf(session.page.html);
    else if (expression === "document.body.innerText") value = bodyText(session.page.html);
    else throw new BrowserError("capability_refused", "only document.title and document.body.innerText are allowed");
    session.actions += 1;
    session.seq += 1;
    return ok("evaluate", session.seq, { value });
  }
  throw new BrowserError("capability_refused", "unsupported browser tool " + String(tool));
}

async function browserCall(alias: string, tool: string, args: Record<string, unknown> | null, state: object | null): Promise<Record<string, unknown>> {
  if (state && typeof state === "object" && (state as { __browser_policy__?: unknown }).__browser_policy__) {
    throw new BrowserError("override", "page text and model state cannot change browser policy");
  }
  const policy = policyFor(alias);
  checkSecrets(policy);
  let session = sessions.get(alias);
  if (!session) {
    session = new Session();
    sessions.set(alias, session);
  }
  return session.exclusive(() => command(session as Session, policy, alias, String(tool || ""), args && typeof args === "object" ? args : {}));
}
'''
