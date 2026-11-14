"""Standalone TypeScript Dataset runtime embedded in the exported graph."""
import json

from ..core.dataset_types import SNAPSHOT_MAX_ROWS
from .dataset_nodes import INPUTS


def typescript_standalone() -> str:
    # The operation names stay aligned with the connected API and the Python standalone runtime.
    inputs = {operation: sorted(names) for operation, names in INPUTS.items()}
    return (STANDALONE.replace("__OPERATION_INPUTS__", json.dumps(inputs, separators=(",", ":")))
            .replace("__SNAPSHOT_MAX_ROWS__", str(SNAPSHOT_MAX_ROWS)))


STANDALONE = r'''
// --- Standalone Dataset storage -------------------------------------------------------------------------------
// SQLite uses node:sqlite (Node 22.13+, or Node 22 with --experimental-sqlite; Deno 2.2+). PostgreSQL uses pg.
const DATASET_OPERATION_INPUTS: Record<string, string[]> = __OPERATION_INPUTS__;
const DATASET_COLUMN_KEY = /^[a-z][a-z0-9_]{0,62}$/;
const DATASET_DATE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;
const DATASET_DATETIME = /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,3})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$/;
const DATASET_EMAIL = /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/;
const DATASET_INVALID_TEXT = /[\u0000\ud800-\udfff]/;
const DATASET_TEXT_KINDS = new Set(["text", "long_text", "url", "email", "select"]);
const DATASET_TIME_KINDS = new Set(["created_time", "updated_time"]);
const DATASET_READ_ONLY = new Set([...DATASET_TIME_KINDS, "auto_number"]);

const DATASET_MAX_TEXT = 16384;
const DATASET_MAX_SAFE_INTEGER = (1 << 53) - 1;
const DATASET_MAX_ROW_BYTES = 65536;
const DATASET_MAX_PAGE_BYTES = 1048576;
const DATASET_MAX_ROWS = 25000;
const DATASET_MAX_SNAPSHOT_ROWS = __SNAPSHOT_MAX_ROWS__;

interface DatasetColumn {
  key: string;
  kind: string;
  required: boolean;
  unique: boolean;
  default: unknown;
  options: string[];
  validation_rules?: { min_length?: number; max_length?: number; min?: number | string; max?: number | string; integer?: boolean; domains?: string[] };
}

interface DatasetFilter {
  field: string;
  op: string;
  value: unknown;
}

interface DatasetFilterGroup { conjunction: "and" | "or"; children: FilterNode[]; }
type FilterNode = DatasetFilter | DatasetFilterGroup;

interface DatasetSort {
  field: string;
  descending: boolean;
}

interface DatasetQuery {
  filters: FilterNode[];
  filterMode: "and" | "or";
  search: string | null;
  sorts: DatasetSort[];
  limit: number;
  offset: number;
}

interface SqlRow {
  [key: string]: unknown;
}

interface SqliteStatement {
  get(...params: unknown[]): SqlRow | undefined;
  all(...params: unknown[]): SqlRow[];
  run(...params: unknown[]): unknown;
}

interface SqliteDatabase {
  exec(sql: string): void;
  prepare(sql: string): SqliteStatement;
  close(): void;
}

interface PgClient {
  connect(): Promise<void>;
  query(sql: string, params?: unknown[]): Promise<{ rows: SqlRow[] }>;
  end(): Promise<void>;
}

interface SqlConnection {
  exec(sql: string): Promise<void>;
  get(sql: string, params?: unknown[]): Promise<SqlRow | undefined>;
  all(sql: string, params?: unknown[]): Promise<SqlRow[]>;
  run(sql: string, params?: unknown[]): Promise<void>;
  transaction<T>(write: boolean, datasetId: string, body: () => Promise<T>): Promise<T>;
  close(): Promise<void>;
}

function datasetFail(code: string, details: Record<string, string | number> = {}): never {
  const extra = Object.entries(details).map(([key, value]) => `${key}=${value}`).join(", ");
  throw new Error(extra ? `${code}: ${extra}` : code);
}

function datasetCliArgs(): string[] {
  const runtime = globalThis as { Deno?: { args?: string[] }; process?: { argv?: string[] } };
  if (Array.isArray(runtime.Deno?.args)) return runtime.Deno.args;
  return Array.isArray(runtime.process?.argv) ? runtime.process.argv.slice(2) : [];
}

function pyString(value: string): string {
  return JSON.stringify(value).replace(/[\u007f-\uffff]/g, (char) => `\\u${char.charCodeAt(0).toString(16).padStart(4, "0")}`);
}

function datasetJson(value: unknown, sort: boolean): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) datasetFail("DATASET_VALUE_INVALID");
    return Number.isInteger(value) ? String(value) : JSON.stringify(value);
  }
  if (typeof value === "string") return pyString(value);
  if (Array.isArray(value)) return `[${value.map((item) => datasetJson(item, sort)).join(",")}]`;
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const keys = Object.keys(record);
    if (sort) keys.sort();
    return `{${keys.map((key) => `${pyString(key)}:${datasetJson(record[key], sort)}`).join(",")}}`;
  }
  datasetFail("DATASET_VALUE_INVALID");
}

function datasetDigest(value: unknown): string {
  return createHash("sha256").update(datasetJson(value, false)).digest("hex");
}

function writeFingerprint(value: unknown): string {
  return createHash("sha256").update(datasetJson(value, true)).digest("hex");
}

function datasetSize(value: unknown): number {
  return new TextEncoder().encode(datasetJson(value, false)).length;
}

function plainObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function datasetColumns(binding: string): DatasetColumn[] {
  const columns = DATASET_BINDINGS[binding]?.columns;
  if (!Array.isArray(columns)) datasetFail("DATASET_BINDING_MISSING", { binding });
  return columns as DatasetColumn[];
}

function datasetContract(binding: string): { version: number; columns: Record<string, DatasetColumn> } {
  const columns: Record<string, DatasetColumn> = {};
  for (const column of datasetColumns(binding)) {
    columns[column.key] = { ...column, options: [...(column.options ?? [])].sort() };
  }
  return { version: 1, columns };
}

function datasetBackend(binding: string): string {
  const setting = `${binding}_BACKEND`;
  const backend = env(setting);
  if (!backend) datasetFail("DATASET_BINDING_MISSING", { setting, choices: "superstep, sqlite, postgresql" });
  if (backend !== "superstep" && backend !== "sqlite" && backend !== "postgresql") {
    datasetFail("DATASET_BINDING_INVALID", { setting, choices: "superstep, sqlite, postgresql" });
  }
  return backend;
}

function datasetId(binding: string): string {
  const value = env(`${binding}_ID`) ?? "";
  if (!/^[A-Za-z0-9_-]{1,100}$/.test(value)) datasetFail("DATASET_BINDING_INVALID", { setting: `${binding}_ID` });
  return value;
}

function sqlitePath(binding: string, setup: boolean): string {
  const setting = `${binding}_SQLITE_PATH`;
  const configured = env(setting);
  if (!configured || configured === ":memory:") datasetFail("DATASET_BINDING_MISSING", { setting });
  const expanded = configured === "~" || configured.startsWith("~/") ? `${homedir()}${configured.slice(1)}` : configured;
  const path = resolve(expanded);
  if (!setup && !existsSync(path)) datasetFail("DATASET_SETUP_REQUIRED", { binding });
  return path;
}

function postgresUrl(binding: string): string {
  const setting = `${binding}_POSTGRES_DSN`;
  const dsn = env(setting);
  if (!dsn) datasetFail("DATASET_BINDING_MISSING", { setting });
  const rewritten = dsn.replace(/^postgres(?:ql)?(?:\+[A-Za-z0-9]+)?:/i, "postgresql:");
  let url: URL;
  try { url = new URL(rewritten); }
  catch { datasetFail("DATASET_BINDING_INVALID", { setting }); }
  if (url.protocol !== "postgresql:" || url.pathname === "" || url.pathname === "/") {
    datasetFail("DATASET_BINDING_INVALID", { setting });
  }
  return rewritten;
}

function pgSql(sql: string): string {
  let index = 0;
  return sql.replace(/\?/g, () => `$${++index}`);
}

async function openSqlite(binding: string, setup: boolean): Promise<SqlConnection> {
  const path = sqlitePath(binding, setup);
  let DatabaseSync: new (location: string) => SqliteDatabase;
  try {
    DatabaseSync = (await import("node:sqlite") as { DatabaseSync: new (location: string) => SqliteDatabase }).DatabaseSync;
  } catch {
    datasetFail("DATASET_STORAGE_ERROR", { binding, requirement: "Node 22.13+ or Deno 2.2+" });
  }
  let db: SqliteDatabase;
  try {
    db = new DatabaseSync(path);
    db.exec("PRAGMA foreign_keys = ON");
    db.exec("PRAGMA busy_timeout = 10000");
  } catch {
    datasetFail("DATASET_STORAGE_ERROR", { binding });
  }
  return {
    async exec(sql) { db.exec(sql); },
    async get(sql, params = []) { return db.prepare(sql).get(...params); },
    async all(sql, params = []) { return db.prepare(sql).all(...params); },
    async run(sql, params = []) { db.prepare(sql).run(...params); },
    async transaction(_write, _datasetId, body) {
      db.exec("BEGIN IMMEDIATE");
      try {
        const result = await body();
        db.exec("COMMIT");
        return result;
      } catch (error) {
        try { db.exec("ROLLBACK"); } catch { /* the failed statement already closed the transaction */ }
        throw error;
      }
    },
    async close() { db.close(); },
  };
}

async function openPostgres(binding: string): Promise<SqlConnection> {
  const connectionString = postgresUrl(binding);
  let Client: new (config: { connectionString: string; connectionTimeoutMillis: number }) => PgClient;
  try {
    const imported = await import("npm:pg@^8") as { default?: { Client: typeof Client }; Client?: typeof Client };
    const ctor = imported.default?.Client ?? imported.Client;
    if (!ctor) datasetFail("DATASET_STORAGE_ERROR", { binding });
    Client = ctor;
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("DATASET_")) throw error;
    datasetFail("DATASET_STORAGE_ERROR", { binding });
  }
  const client = new Client({ connectionString, connectionTimeoutMillis: 10000 });
  try { await client.connect(); }
  catch { datasetFail("DATASET_STORAGE_ERROR", { binding }); }
  const query = async (sql: string, params: unknown[] = []) => client.query(pgSql(sql), params);
  return {
    async exec(sql) { await client.query(sql); },
    async get(sql, params = []) { return (await query(sql, params)).rows[0]; },
    async all(sql, params = []) { return (await query(sql, params)).rows; },
    async run(sql, params = []) { await query(sql, params); },
    async transaction(write, datasetId, body) {
      await client.query("BEGIN");
      try {
        if (write) await client.query("SELECT dataset_id FROM superstep_dataset_definitions WHERE dataset_id = $1 FOR UPDATE", [datasetId]);
        const result = await body();
        await client.query("COMMIT");
        return result;
      } catch (error) {
        try { await client.query("ROLLBACK"); } catch { /* the connection is discarded by close() */ }
        throw error;
      }
    },
    async close() { await client.end(); },
  };
}

async function openDataset(binding: string, backend: string, setup: boolean): Promise<[SqlConnection, string]> {
  try {
    const connection = backend === "sqlite" ? await openSqlite(binding, setup) : await openPostgres(binding);
    return [connection, datasetId(binding)];
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("DATASET_")) throw error;
    datasetFail("DATASET_STORAGE_ERROR", { binding });
  }
}

const DATASET_DDL = [
  `CREATE TABLE IF NOT EXISTS superstep_dataset_definitions (
    dataset_id VARCHAR(100) PRIMARY KEY,
    contract TEXT NOT NULL,
    auto_number_counter BIGINT NOT NULL DEFAULT 0)`,
  `CREATE TABLE IF NOT EXISTS superstep_dataset_rows (
    dataset_id VARCHAR(100) NOT NULL REFERENCES superstep_dataset_definitions (dataset_id),
    id VARCHAR(32) NOT NULL,
    "values" TEXT NOT NULL,
    revision INTEGER NOT NULL,
    created DOUBLE PRECISION NOT NULL,
    updated DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (dataset_id, id))`,
  `CREATE INDEX IF NOT EXISTS ix_superstep_dataset_rows_order ON superstep_dataset_rows (dataset_id, created, id)`,
  `CREATE TABLE IF NOT EXISTS superstep_dataset_keys (
    dataset_id VARCHAR(100) NOT NULL,
    field VARCHAR(63) NOT NULL,
    digest VARCHAR(64) NOT NULL,
    row_id VARCHAR(32) NOT NULL,
    PRIMARY KEY (dataset_id, field, digest),
    FOREIGN KEY (dataset_id, row_id) REFERENCES superstep_dataset_rows (dataset_id, id))`,
  `CREATE INDEX IF NOT EXISTS ix_superstep_dataset_keys_row ON superstep_dataset_keys (dataset_id, row_id)`,
  `CREATE TABLE IF NOT EXISTS superstep_dataset_receipts (
    dataset_id VARCHAR(100) NOT NULL REFERENCES superstep_dataset_definitions (dataset_id),
    operation_id VARCHAR(128) NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    result TEXT NOT NULL,
    created DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (dataset_id, operation_id))`,
];

function storedJson(value: unknown, binding: string): Record<string, unknown> {
  if (typeof value === "string") {
    try { return JSON.parse(value) as Record<string, unknown>; }
    catch { datasetFail("DATASET_STORAGE_ERROR", { binding }); }
  }
  if (plainObject(value)) return value;
  datasetFail("DATASET_STORAGE_ERROR", { binding });
}

async function datasetStorageReady(connection: SqlConnection, binding: string): Promise<void> {
  try {
    await connection.get('SELECT dataset_id FROM superstep_dataset_definitions LIMIT 1');
    await connection.get('SELECT dataset_id FROM superstep_dataset_rows LIMIT 1');
    await connection.get('SELECT dataset_id FROM superstep_dataset_keys LIMIT 1');
    await connection.get('SELECT created FROM superstep_dataset_receipts LIMIT 1');
  } catch {
    datasetFail("DATASET_SETUP_REQUIRED", { binding });
  }
}

async function datasetMigrateReceipts(connection: SqlConnection, backend: string, binding: string): Promise<void> {
  const postgres = backend === "postgresql";
  if (postgres) await connection.exec("LOCK TABLE superstep_dataset_receipts IN ACCESS EXCLUSIVE MODE");
  const columns = postgres
    ? await connection.all("SELECT attname AS name FROM pg_attribute WHERE attrelid = 'superstep_dataset_receipts'::regclass AND attnum > 0 AND NOT attisdropped")
    : await connection.all("PRAGMA table_info(superstep_dataset_receipts)");
  if (columns.some((column) => column.name === "created")) return;
  await connection.exec("ALTER TABLE superstep_dataset_receipts ADD COLUMN created DOUBLE PRECISION NOT NULL DEFAULT 0");
  const now = Date.now() / 1000;
  let anchor: unknown[] = [];
  while (true) {
    const predicate = anchor.length ? "WHERE (dataset_id, operation_id) > (?, ?)" : "";
    const batch = await connection.all(
      `SELECT dataset_id, operation_id, result FROM superstep_dataset_receipts ${predicate} ORDER BY dataset_id, operation_id LIMIT 200`, anchor,
    );
    if (!batch.length) return;
    for (const receipt of batch) {
      const old = storedJson(receipt.result, binding);
      const result = plainObject(old.row) ? { row_id: old.row.id, revision: old.row.revision, inserted: old.inserted } : old;
      await connection.run("UPDATE superstep_dataset_receipts SET result = ?, created = ? WHERE dataset_id = ? AND operation_id = ?",
        [datasetJson(result, true), now, receipt.dataset_id, receipt.operation_id]);
    }
    const last = batch[batch.length - 1];
    anchor = [last.dataset_id, last.operation_id];
  }
}

async function datasetExpireReceipts(connection: SqlConnection, datasetIdValue: string): Promise<void> {
  const setting = env("STUDIO_DATASET_RECEIPT_DAYS")?.trim() ?? "";
  const days = /^[-+]?\d+$/.test(setting) ? Math.max(1, Number(setting)) : 30;
  await connection.run("DELETE FROM superstep_dataset_receipts WHERE dataset_id = ? AND created < ?",
    [datasetIdValue, Date.now() / 1000 - days * 86400]);
}

async function datasetSchemasMatch(connection: SqlConnection, datasetIdValue: string, binding: string): Promise<void> {
  const row = await connection.get("SELECT contract FROM superstep_dataset_definitions WHERE dataset_id = ?", [datasetIdValue]);
  if (!row) datasetFail("DATASET_SETUP_REQUIRED", { binding });
  const stored = storedJson(row.contract, binding);
  if (datasetJson(stored, true) !== datasetJson(datasetContract(binding), true)) {
    datasetFail("DATASET_BINDING_SCHEMA_MISMATCH", { binding });
  }
}

async function datasetRestoreSnapshot(connection: SqlConnection, datasetIdValue: string, binding: string): Promise<void> {
  const path = resolve(dirname(fileURLToPath(import.meta.url)), "dataset-snapshots.json");
  if (!existsSync(path)) return;
  let document: { snapshots?: unknown };
  try { document = JSON.parse(readFileSync(path, "utf8")) as { snapshots?: unknown }; }
  catch { datasetFail("DATASET_SNAPSHOT_INVALID", { binding }); }
  if (!Array.isArray(document.snapshots)) datasetFail("DATASET_SNAPSHOT_INVALID", { binding });
  const chosen = document.snapshots.find((item) => plainObject(item) && item.binding === binding) as { binding?: string; contract?: unknown; rows?: unknown } | undefined;
  if (!chosen) return;
  const contract = datasetContract(binding);
  if (!plainObject(chosen.contract) || datasetJson(chosen.contract, true) !== datasetJson(contract, true)) {
    datasetFail("DATASET_BINDING_SCHEMA_MISMATCH", { binding });
  }
  if (!Array.isArray(chosen.rows)) datasetFail("DATASET_SNAPSHOT_INVALID", { binding });
  if (chosen.rows.length > DATASET_MAX_SNAPSHOT_ROWS) datasetFail("DATASET_SNAPSHOT_TOO_LARGE", { max: DATASET_MAX_SNAPSHOT_ROWS });
  const columns = contract.columns;
  const prepared: { id: string; values: Record<string, unknown>; created: number; updated: number }[] = [];
  for (const item of chosen.rows) {
    if (!plainObject(item) || typeof item.id !== "string" || !/^[a-f0-9]{32}$/.test(item.id) || !plainObject(item.values)) {
      datasetFail("DATASET_SNAPSHOT_INVALID", { binding });
    }
    if (Object.keys(item.values).some((key) => !columns[key])) datasetFail("DATASET_BINDING_SCHEMA_MISMATCH", { binding });
    const stored: Record<string, unknown> = {};
    try {
      for (const [field, column] of Object.entries(columns)) {
        if (DATASET_TIME_KINDS.has(column.kind)) continue;
        stored[field] = datasetNormalize(column, Object.hasOwn(item.values, field) ? item.values[field] : column.default, column.required);
      }
    } catch (error) {
      if (error instanceof Error && error.message.startsWith("DATASET_")) datasetFail("DATASET_BINDING_SCHEMA_MISMATCH", { binding });
      throw error;
    }
    if (datasetSize(stored) > DATASET_MAX_ROW_BYTES) datasetFail("DATASET_ROW_TOO_LARGE", { max: DATASET_MAX_ROW_BYTES });
    const now = Date.now() / 1000;
    const created = item.created ?? now;
    const updated = item.updated ?? now;
    if (typeof created !== "number" || typeof updated !== "number") datasetFail("DATASET_SNAPSHOT_INVALID", { binding });
    prepared.push({ id: item.id, values: stored, created, updated });
  }
  const auto = Object.values(columns).filter(column => column.kind === "auto_number");
  const watermark = Math.max(0, ...prepared.flatMap(row => auto.map(column => Number(row.values[column.key] ?? 0))));
  if (watermark) await connection.run(
    "UPDATE superstep_dataset_definitions SET auto_number_counter = ? WHERE dataset_id = ? AND auto_number_counter < ?",
    [watermark, datasetIdValue, watermark],
  );
  for (const row of prepared) {
    const existing = await connection.get("SELECT id FROM superstep_dataset_rows WHERE dataset_id = ? AND id = ?", [datasetIdValue, row.id]);
    if (existing) continue;
    const count = Number((await connection.get("SELECT COUNT(*) AS n FROM superstep_dataset_rows WHERE dataset_id = ?", [datasetIdValue]))?.n ?? 0);
    if (count >= DATASET_MAX_ROWS) datasetFail("DATASET_ROW_LIMIT", { max: DATASET_MAX_ROWS });
    await connection.run(
      'INSERT INTO superstep_dataset_rows (dataset_id, id, "values", revision, created, updated) VALUES (?, ?, ?, ?, ?, ?)',
      [datasetIdValue, row.id, datasetJson(row.values, false), 1, row.created, row.updated],
    );
    for (const [field, column] of Object.entries(columns)) {
      if (!column.unique || row.values[field] === null || row.values[field] === undefined) continue;
      try {
        await connection.run(
          "INSERT INTO superstep_dataset_keys (dataset_id, field, digest, row_id) VALUES (?, ?, ?, ?)",
          [datasetIdValue, field, datasetDigest(row.values[field]), row.id],
        );
      } catch (error) {
        if (isUniqueViolation(error)) datasetFail("DATASET_UNIQUE_CONFLICT");
        throw error;
      }
    }
  }
}

export async function setupDatasets(create: boolean): Promise<void> {
  for (const binding of Object.keys(DATASET_BINDINGS)) {
    const backend = datasetBackend(binding);
    if (backend === "superstep") continue;
    const [connection, datasetIdValue] = await openDataset(binding, backend, create);
    try {
      await connection.transaction(create && backend === "sqlite", datasetIdValue, async () => {
        if (create) {
          for (const statement of DATASET_DDL) await connection.exec(statement);
          if (backend === "postgresql") {
            await connection.exec("ALTER TABLE superstep_dataset_definitions ADD COLUMN IF NOT EXISTS auto_number_counter BIGINT NOT NULL DEFAULT 0");
          } else if (!(await connection.all("PRAGMA table_info(superstep_dataset_definitions)")).some(col => col.name === "auto_number_counter")) {
            await connection.exec("ALTER TABLE superstep_dataset_definitions ADD COLUMN auto_number_counter BIGINT NOT NULL DEFAULT 0");
          }
          await datasetMigrateReceipts(connection, backend, binding);
          await connection.run(
            `INSERT INTO superstep_dataset_definitions (dataset_id, contract) VALUES (?, ?)
             ON CONFLICT (dataset_id) DO NOTHING`,
            [datasetIdValue, datasetJson(datasetContract(binding), true)],
          );
        } else {
          await datasetStorageReady(connection, binding);
        }
        await datasetSchemasMatch(connection, datasetIdValue, binding);
        if (create) await datasetRestoreSnapshot(connection, datasetIdValue, binding);
      });
    } catch (error) {
      if (error instanceof Error && error.message.startsWith("DATASET_")) throw error;
      datasetFail("DATASET_STORAGE_ERROR", { binding });
    } finally {
      await connection.close();
    }
  }
}

function datasetColumn(columns: Record<string, DatasetColumn>, field: string): DatasetColumn {
  const column = columns[field];
  if (!column) datasetFail("DATASET_COLUMN_NOT_FOUND", { field });
  return column;
}

function datasetNormalize(column: DatasetColumn, value: unknown, required: boolean, validateRule = true): unknown {
  const normalized = datasetNormalizeType(column, value, required);
  const rule = validateRule && column.validation_rules;
  if (rule && normalized !== null) {
    const text = typeof normalized === "string" ? normalized : "";
    const size = [...text].length;
    if ((rule.min_length !== undefined && size < rule.min_length) || (rule.max_length !== undefined && size > rule.max_length)
        || (rule.integer && !Number.isInteger(normalized))
        || (rule.domains && !rule.domains.includes(text.slice(text.lastIndexOf("@") + 1)))
        || (rule.min !== undefined && compareValue(column.kind, normalized, rule.min) < 0)
        || (rule.max !== undefined && compareValue(column.kind, normalized, rule.max) > 0)) {
      datasetFail("DATASET_COLUMN_RULE_VIOLATION", { field: column.key });
    }
  }
  return normalized;
}

function datasetNormalizeType(column: DatasetColumn, value: unknown, required: boolean): unknown {
  if (value === null && !required) return null;
  if (column.kind === "multi_select" && Array.isArray(value)) {
    if (!value.length && !required) return null;
    if (value.length && new Set(value).size === value.length && value.every(item => typeof item === "string" && column.options.includes(item))) {
      return column.options.filter(option => value.includes(option));
    }
  }
  if (column.kind === "auto_number" && typeof value === "number" && Number.isSafeInteger(value) && value > 0) return value;
  if (column.kind === "boolean" && typeof value === "boolean") return value;
  if (column.kind === "number" && typeof value === "number" && Number.isFinite(value) && Math.abs(value) <= DATASET_MAX_SAFE_INTEGER) {
    return value;
  }
  if (typeof value === "string" && !DATASET_INVALID_TEXT.test(value)) {
    if ((column.kind === "text" || column.kind === "long_text") && [...value].length <= DATASET_MAX_TEXT) return value;
    if (column.kind === "url" && value.length <= 2048 && /^https?:\/\//i.test(value) && !/[\s\u0000-\u001f\u007f\\]/u.test(value)) {
      try {
        const url = new URL(value);
        if (url.hostname && !url.username && !url.password) return value;
      } catch { /* Report invalid field below. */ }
    }
    if (column.kind === "select" && column.options.includes(value)) return value;
    if (column.kind === "email") {
      const email = value.trim();
      if (email.length <= 254 && DATASET_EMAIL.test(email)) return email.toLowerCase();
    }
    if (column.kind === "date" && DATASET_DATE.test(value)) {
      const [year, month, day] = value.split("-").map(Number);
      const date = new Date(Date.UTC(year, month - 1, day));
      if (date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day) return value;
    }
    if ((column.kind === "datetime" || DATASET_TIME_KINDS.has(column.kind)) && DATASET_DATETIME.test(value)) {
      const parsed = new Date(value);
      if (!Number.isNaN(parsed.getTime())) return parsed.toISOString();
    }
  }
  datasetFail("DATASET_VALUE_INVALID", { field: column.key, kind: column.kind });
}

function filterOperators(kind: string): string[] {
  if (kind === "multi_select") return ["contains_any", "contains_all", "is_null"];
  if (kind === "boolean") return ["eq", "ne", "is_null", "not_null", "in", "not_in"];
  const operators = ["eq", "ne", "lt", "lte", "gt", "gte", "is_null", "not_null", "in", "not_in"];
  if (DATASET_TEXT_KINDS.has(kind)) operators.splice(6, 0, "contains", "not_contains");
  return operators;
}

function compareText(left: string, right: string): number {
  const encoder = new TextEncoder();
  const a = encoder.encode(left);
  const b = encoder.encode(right);
  const length = Math.min(a.length, b.length);
  for (let index = 0; index < length; index++) {
    if (a[index] !== b[index]) return a[index] < b[index] ? -1 : 1;
  }
  return a.length === b.length ? 0 : a.length < b.length ? -1 : 1;
}

function compareValue(kind: string, left: unknown, right: unknown): number {
  if (kind === "number" || kind === "auto_number") return Number(left) < Number(right) ? -1 : Number(left) > Number(right) ? 1 : 0;
  if (kind === "boolean") return Number(left) - Number(right);
  return compareText(String(left), String(right));
}

function valuesEqual(kind: string, left: unknown, right: unknown): boolean {
  if (kind === "number" || kind === "auto_number") return Number(left) === Number(right);
  return Array.isArray(left) && Array.isArray(right) ? datasetJson(left, true) === datasetJson(right, true) : left === right;
}

function rowValue(row: SqlRow, values: Record<string, unknown>, column: DatasetColumn): unknown {
  if (DATASET_TIME_KINDS.has(column.kind)) {
    const stamp = Number(column.kind === "created_time" ? row.created : row.updated);
    return new Date(Math.floor(stamp * 1000)).toISOString();
  }
  return values[column.key] ?? null;
}

function datasetRow(row: SqlRow, fields: string[], binding: string): Record<string, unknown> {
  const values = storedJson(row.payload ?? row.values, binding);
  const projected: Record<string, unknown> = {};
  const columns = datasetContract(binding).columns;
  for (const field of fields) projected[field] = rowValue(row, values, columns[field]);
  return {
    id: String(row.id),
    revision: Number(row.revision),
    created: Number(row.created),
    updated: Number(row.updated),
    values: projected,
  };
}

function integerArg(value: unknown, name: string, min: number, max: number, fallback: number): number {
  if (value === undefined) return fallback;
  if (typeof value !== "number" || !Number.isInteger(value) || value < min || value > max) {
    datasetFail("DATASET_NODE_ARGUMENTS_INVALID", { field: name });
  }
  return value;
}

function parseQuery(argumentsValue: Record<string, unknown>, columns: Record<string, DatasetColumn>): DatasetQuery {
  const filters: FilterNode[] = [];
  let ruleCount = 0;
  function parseRule(value: unknown, tagged: boolean): DatasetFilter {
    if (!plainObject(value) || typeof value.field !== "string" || typeof value.op !== "string"
        || Object.keys(value).some(key => !["field", "op", "value", ...(tagged ? ["type"] : [])].includes(key))) {
      datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
    }
    const column = datasetColumn(columns, value.field);
    if (!filterOperators(column.kind).includes(value.op)) datasetFail("DATASET_FILTER_INVALID", { field: column.key });
    let operand: unknown = value.value ?? null;
    if (["is_null", "not_null"].includes(value.op)) {
      if (operand !== null) datasetFail("DATASET_FILTER_INVALID", { field: column.key });
    } else if (["contains", "not_contains"].includes(value.op)) {
      if (typeof operand !== "string" || !operand.length || [...operand].length > 120 || DATASET_INVALID_TEXT.test(operand)) {
        datasetFail("DATASET_FILTER_INVALID", { field: column.key });
      }
    } else if (["in", "not_in", "contains_any", "contains_all"].includes(value.op)) {
      if (!Array.isArray(operand) || !operand.length || operand.length > 50) datasetFail("DATASET_FILTER_INVALID", { field: column.key });
      operand = column.kind === "multi_select" ? datasetNormalize(column, operand, true, false)
        : operand.map(item => datasetNormalize(column, item, true, false));
    } else operand = datasetNormalize(column, operand, true, false);
    return { field: column.key, op: value.op, value: operand };
  }

  function parseGroup(value: unknown, depth: number): DatasetFilterGroup {
    if (depth > 3 || !plainObject(value) || value.type !== "group"
        || (value.conjunction !== "and" && value.conjunction !== "or") || Object.keys(value).length !== 3
        || !Array.isArray(value.children) || !value.children.length || value.children.length > 20) {
      datasetFail("DATASET_FILTER_INVALID");
    }
    const children = value.children.map(child => {
      if (plainObject(child) && child.type === "group") return parseGroup(child, depth + 1);
      if (!plainObject(child) || child.type !== "rule" || ++ruleCount > 20) datasetFail("DATASET_FILTER_INVALID");
      return parseRule(child, true);
    });
    return { conjunction: value.conjunction, children };
  }

  if (argumentsValue.filter_tree !== undefined && argumentsValue.filter_tree !== null) {
    if (Object.hasOwn(argumentsValue, "filters") || Object.hasOwn(argumentsValue, "filter_mode")) datasetFail("DATASET_FILTER_INVALID");
    filters.push(parseGroup(argumentsValue.filter_tree, 1));
  } else {
    const rawFilters = argumentsValue.filters ?? [];
    if (!Array.isArray(rawFilters) || rawFilters.length > 12) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
    filters.push(...rawFilters.map(rule => parseRule(rule, false)));
  }
  const sorts: DatasetSort[] = [];
  const rawSorts = argumentsValue.sorts ?? [];
  if (!Array.isArray(rawSorts) || rawSorts.length > 12) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  for (const rule of rawSorts) {
    if (!plainObject(rule) || typeof rule.field !== "string" || Object.keys(rule).some((key) => !["field", "descending"].includes(key))) {
      datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
    }
    if (rule.descending !== undefined && typeof rule.descending !== "boolean") datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
    if (!DATASET_COLUMN_KEY.test(rule.field) || !columns[rule.field]) datasetFail("DATASET_COLUMN_NOT_FOUND", { field: rule.field });
    sorts.push({ field: rule.field, descending: rule.descending === true });
  }
  const mode = argumentsValue.filter_mode ?? "and";
  if (mode !== "and" && mode !== "or") datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  const search = argumentsValue.search ?? null;
  if (search !== null && (typeof search !== "string" || search.length > 120)) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  return {
    filters,
    filterMode: mode,
    search,
    sorts,
    limit: integerArg(argumentsValue.limit, "limit", 1, 100, 50),
    offset: integerArg(argumentsValue.offset, "offset", 0, DATASET_MAX_ROWS, 0),
  };
}

function rowMatches(row: SqlRow, query: DatasetQuery, columns: Record<string, DatasetColumn>, keyHits: Map<string, Set<string>>, binding: string): boolean {
  const values = storedJson(row.payload ?? row.values, binding);
  function check(rule: FilterNode): boolean {
    if ("children" in rule) return rule.conjunction === "or" ? rule.children.some(check) : rule.children.every(check);
    const column = columns[rule.field];
    const current = rowValue(row, values, column);
    if (rule.op === "is_null" || rule.op === "not_null") return rule.op === "is_null" ? current === null : current !== null;
    if (rule.op === "contains" || rule.op === "not_contains") {
      const contains = typeof current === "string" && current.toLowerCase().includes((rule.value as string).toLowerCase());
      return rule.op === "contains" ? contains : !contains;
    }
    if (rule.op === "contains_any" || rule.op === "contains_all") {
      if (!Array.isArray(current)) return false;
      const options = rule.value as string[];
      return rule.op === "contains_any" ? options.some(item => current.includes(item)) : options.every(item => current.includes(item));
    }
    const expected = rule.value;
    const equal = (value: unknown) => column.unique && (rule.op === "eq" || rule.op === "in")
      ? keyHits.get(`${rule.field}:${datasetDigest(value)}`)?.has(String(row.id)) === true
      : current !== null && valuesEqual(column.kind, current, value);
    if (rule.op === "in" || rule.op === "not_in") {
      const included = (expected as unknown[]).some(equal);
      return rule.op === "in" ? included : !included;
    }
    if (rule.op === "eq" || rule.op === "ne") return rule.op === "eq" ? equal(expected) : !equal(expected);
    if (current === null) return false;
    const compared = compareValue(column.kind, current, expected);
    if (rule.op === "lt") return compared < 0;
    if (rule.op === "lte") return compared <= 0;
    if (rule.op === "gt") return compared > 0;
    return compared >= 0;
  }
  const checks = query.filters.map(check);
  if (checks.length && !(query.filterMode === "or" ? checks.some(Boolean) : checks.every(Boolean))) return false;
  if (query.search) {
    if (DATASET_INVALID_TEXT.test(query.search)) datasetFail("DATASET_FILTER_INVALID", { field: "search" });
    const terms = Object.values(columns).filter((column) => DATASET_TEXT_KINDS.has(column.kind));
    if (!terms.length) return false;
    if (!terms.some((column) => typeof values[column.key] === "string" && (values[column.key] as string).toLowerCase().includes(query.search!.toLowerCase()))) return false;
  }
  return true;
}

async function matchingRows(connection: SqlConnection, datasetIdValue: string, columns: Record<string, DatasetColumn>, query: DatasetQuery, binding: string) {
  const rows = await connection.all(
    'SELECT id, "values" AS payload, revision, created, updated FROM superstep_dataset_rows WHERE dataset_id = ?',
    [datasetIdValue],
  );
  const keyHits = new Map<string, Set<string>>();
  function flatten(nodes: FilterNode[]): DatasetFilter[] {
    return nodes.flatMap(item => "children" in item ? flatten(item.children) : [item]);
  }
  for (const rule of flatten(query.filters)) {
    if (!columns[rule.field].unique || (rule.op !== "eq" && rule.op !== "in")) continue;
    for (const expected of rule.op === "in" ? rule.value as unknown[] : [rule.value]) {
      const digest = datasetDigest(expected);
      const hits = await connection.all(
        "SELECT row_id FROM superstep_dataset_keys WHERE dataset_id = ? AND field = ? AND digest = ?",
        [datasetIdValue, rule.field, digest],
      );
      keyHits.set(`${rule.field}:${digest}`, new Set(hits.map(hit => String(hit.row_id))));
    }
  }
  return rows.filter(row => rowMatches(row, query, columns, keyHits, binding));
}

async function datasetFind(connection: SqlConnection, datasetIdValue: string, columns: Record<string, DatasetColumn>, fields: string[], argumentsValue: Record<string, unknown>, binding: string): Promise<Record<string, unknown>> {
  const query = parseQuery(argumentsValue, columns);
  const matched = await matchingRows(connection, datasetIdValue, columns, query, binding);
  matched.sort((left, right) => {
    const leftValues = storedJson(left.payload, binding);
    const rightValues = storedJson(right.payload, binding);
    for (const sort of query.sorts) {
      const column = datasetColumn(columns, sort.field);
      const a = rowValue(left, leftValues, column);
      const b = rowValue(right, rightValues, column);
      if (a === null || b === null) {
        if (a !== b) return a === null ? 1 : -1;
        continue;
      }
      const folded = typeof a === "string" && typeof b === "string" ? compareText(a.toLowerCase(), b.toLowerCase()) : 0;
      const compared = folded || compareValue(column.kind, a, b);
      if (compared !== 0) return sort.descending ? -compared : compared;
    }
    if (!query.sorts.length && Number(left.created) !== Number(right.created)) return Number(left.created) < Number(right.created) ? -1 : 1;
    return String(left.id) < String(right.id) ? -1 : String(left.id) > String(right.id) ? 1 : 0;
  });
  const items: Record<string, unknown>[] = [];
  let remaining = DATASET_MAX_PAGE_BYTES;
  for (const row of matched.slice(query.offset)) {
    if (items.length === query.limit) return { items, next_offset: query.offset + items.length, schema_revision: 1 };
    const item = datasetRow(row, fields, binding);
    remaining -= datasetSize(item);
    if (remaining < 0) return { items, next_offset: query.offset + items.length, schema_revision: 1 };
    items.push(item);
  }
  return { items, next_offset: null, schema_revision: 1 };
}

async function datasetAggregate(connection: SqlConnection, datasetIdValue: string, columns: Record<string, DatasetColumn>, fields: string[], args: Record<string, unknown>, binding: string) {
  const groupBy = args.group_by ?? null;
  if (groupBy !== null && (typeof groupBy !== "string" || !fields.includes(groupBy))) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  if (!plainObject(args.summaries) || !Object.keys(args.summaries).length) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  const functions = new Map<string, string>();
  for (const [field, op] of Object.entries(args.summaries)) {
    if (!fields.includes(field)) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
    const kind = columns[field].kind;
    const supported = ["count", "empty_count", "empty_percent", "unique_count"];
    if (kind === "number" || kind === "auto_number") supported.push("sum", "avg", "min", "max");
    if (kind === "date" || kind === "datetime" || DATASET_TIME_KINDS.has(kind)) supported.push("min", "max");
    if (typeof op !== "string" || !supported.includes(op)) datasetFail("DATASET_SUMMARY_INVALID", { field });
    functions.set(field, op);
  }
  const query = parseQuery(args, columns);
  const rows = await matchingRows(connection, datasetIdValue, columns, query, binding);
  const groups = new Map<string, { group: unknown; rows: SqlRow[] }>();
  if (groupBy === null) groups.set("null", { group: null, rows });
  else for (const row of rows) {
    const value = rowValue(row, storedJson(row.payload, binding), columns[groupBy]);
    const key = datasetJson(value, true);
    if (!groups.has(key)) groups.set(key, { group: value, rows: [] });
    groups.get(key)!.rows.push(row);
  }
  const ordered = [...groups.values()].sort((left, right) => right.rows.length - left.rows.length
    || (left.group === null ? Number(right.group !== null) : right.group === null ? -1
      : compareValue(columns[groupBy!].kind, left.group, right.group)));
  return {
    group_by: groupBy,
    truncated: ordered.length > 20,
    groups: ordered.slice(0, 20).map(({ group, rows }) => ({
      group,
      total: rows.length,
      values: Object.fromEntries([...functions].map(([field, op]) => {
        const column = columns[field];
        const values = rows.map(row => rowValue(row, storedJson(row.payload, binding), column)).filter(value => value !== null);
        const empty = rows.length - values.length;
        if (op === "count") return [field, values.length];
        if (op === "empty_count") return [field, empty];
        if (op === "empty_percent") return [field, rows.length ? 100 * empty / rows.length : null];
        if (op === "unique_count") return [field, new Set(values.map(value => datasetJson(value, true))).size];
        if (!values.length) return [field, null];
        if (op === "sum" || op === "avg") {
          const sum = values.reduce<number>((total, value) => total + Number(value), 0);
          return [field, op === "avg" ? sum / values.length : sum];
        }
        return [field, values.slice(1).reduce((result, value) => {
          const order = compareValue(column.kind, value, result);
          return (op === "min" ? order < 0 : order > 0) ? value : result;
        }, values[0])];
      })),
    })),
  };
}


function isUniqueViolation(error: unknown): boolean {
  const code = (error as { code?: string }).code;
  const message = error instanceof Error ? error.message : String(error);
  return code === "23505" || /UNIQUE constraint failed|duplicate key value/i.test(message);
}

async function datasetWrite(connection: SqlConnection, datasetIdValue: string, columns: Record<string, DatasetColumn>, operation: string, fields: string[], argumentsValue: Record<string, unknown>, operationId: string, binding: string): Promise<Record<string, unknown>> {
  if (!/^[A-Za-z0-9_.:-]{1,128}$/.test(operationId)) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  const allowed = operation === "upsert_row" ? ["values", "key"] : ["values"];
  if (Object.keys(argumentsValue).some((key) => !allowed.includes(key)) || !plainObject(argumentsValue.values)) {
    datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  }
  if (Object.keys(argumentsValue.values).length > 100) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  const incoming: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(argumentsValue.values)) {
    const column = datasetColumn(columns, key);
    if (DATASET_READ_ONLY.has(column.kind)) datasetFail("DATASET_COLUMN_READ_ONLY", { field: key });
    incoming[key] = datasetNormalize(column, value, column.required);
  }
  const key = operation === "upsert_row" ? argumentsValue.key : null;
  if (operation === "upsert_row" && (typeof key !== "string" || !datasetColumn(columns, key).unique || incoming[key] === null || incoming[key] === undefined)) {
    datasetFail("DATASET_UPSERT_KEY_INVALID", { field: String(key) });
  }
  const fingerprint = writeFingerprint({
    arguments: operation === "upsert_row"
      ? { key, schema_revision: null, values: argumentsValue.values }
      : { schema_revision: null, values: argumentsValue.values },
    fields,
    operation,
  });
  const previous = await connection.get(
    "SELECT fingerprint, result FROM superstep_dataset_receipts WHERE dataset_id = ? AND operation_id = ?",
    [datasetIdValue, operationId],
  );
  if (previous) {
    if (previous.fingerprint !== fingerprint) datasetFail("DATASET_RECEIPT_CONFLICT");
    const result = storedJson(previous.result, binding);
    const current = await connection.get(
      'SELECT id, "values" AS payload, revision, created, updated FROM superstep_dataset_rows WHERE dataset_id = ? AND id = ?',
      [datasetIdValue, result.row_id],
    );
    const row = current && fields.length ? datasetRow(current, fields, binding)
      : { id: result.row_id, revision: current ? Number(current.revision) : result.revision };
    return { row, inserted: result.inserted };
  }
  let existing: SqlRow | undefined;
  if (typeof key === "string") {
    const hit = await connection.get(
      "SELECT row_id FROM superstep_dataset_keys WHERE dataset_id = ? AND field = ? AND digest = ?",
      [datasetIdValue, key, datasetDigest(incoming[key])],
    );
    if (hit) {
      existing = await connection.get(
        'SELECT id, "values" AS payload, revision, created, updated FROM superstep_dataset_rows WHERE dataset_id = ? AND id = ?',
        [datasetIdValue, hit.row_id],
      );
    }
  }
  let rowValues: Record<string, unknown>;
  if (!existing) {
    const count = Number((await connection.get("SELECT COUNT(*) AS n FROM superstep_dataset_rows WHERE dataset_id = ?", [datasetIdValue]))?.n ?? 0);
    if (count >= DATASET_MAX_ROWS) datasetFail("DATASET_ROW_LIMIT", { max: DATASET_MAX_ROWS });
    rowValues = {};
    const autoColumns = Object.values(columns).filter(column => column.kind === "auto_number");
    if (autoColumns.length) {
      const counter = await connection.get(
        "UPDATE superstep_dataset_definitions SET auto_number_counter = auto_number_counter + 1 WHERE dataset_id = ? RETURNING auto_number_counter",
        [datasetIdValue],
      );
      for (const column of autoColumns) rowValues[column.key] = Number(counter?.auto_number_counter);
    }
    for (const [field, column] of Object.entries(columns)) {
      if (!DATASET_READ_ONLY.has(column.kind)) {
        rowValues[field] = Object.hasOwn(incoming, field) ? incoming[field] : datasetNormalize(column, column.default, column.required);
      }
    }
  } else {
    rowValues = { ...storedJson(existing.payload, binding), ...incoming };
  }
  if (datasetSize(rowValues) > DATASET_MAX_ROW_BYTES) datasetFail("DATASET_ROW_TOO_LARGE", { max: DATASET_MAX_ROW_BYTES });
  const now = Date.now() / 1000;
  const rowId = existing ? String(existing.id) : crypto.randomUUID().replace(/-/g, "");
  const changed = !existing || datasetJson(rowValues, true) !== datasetJson(storedJson(existing.payload, binding), true);
  if (!existing) {
    await connection.run(
      'INSERT INTO superstep_dataset_rows (dataset_id, id, "values", revision, created, updated) VALUES (?, ?, ?, ?, ?, ?)',
      [datasetIdValue, rowId, datasetJson(rowValues, false), 1, now, now],
    );
  } else if (changed) {
    await connection.run(
      'UPDATE superstep_dataset_rows SET "values" = ?, revision = ?, updated = ? WHERE dataset_id = ? AND id = ?',
      [datasetJson(rowValues, false), Number(existing.revision) + 1, now, datasetIdValue, rowId],
    );
    await connection.run("DELETE FROM superstep_dataset_keys WHERE dataset_id = ? AND row_id = ?", [datasetIdValue, rowId]);
  }
  for (const [field, column] of Object.entries(columns)) {
    if (!changed || !column.unique || rowValues[field] === null || rowValues[field] === undefined) continue;
    try {
      await connection.run(
        "INSERT INTO superstep_dataset_keys (dataset_id, field, digest, row_id) VALUES (?, ?, ?, ?)",
        [datasetIdValue, field, datasetDigest(rowValues[field]), rowId],
      );
    } catch (error) {
      if (isUniqueViolation(error)) datasetFail("DATASET_UNIQUE_CONFLICT");
      throw error;
    }
  }
  const stored = await connection.get(
    'SELECT id, "values" AS payload, revision, created, updated FROM superstep_dataset_rows WHERE dataset_id = ? AND id = ?',
    [datasetIdValue, rowId],
  );
  if (!stored) datasetFail("DATASET_STORAGE_ERROR", { binding });
  // An empty field list asks for identifiers only, the shape a write-only connected token receives.
  const outcome = fields.length ? datasetRow(stored, fields, binding) : { id: String(stored.id), revision: Number(stored.revision) };
  const result = { inserted: !existing, row: outcome };
  await connection.run(
    "INSERT INTO superstep_dataset_receipts (dataset_id, operation_id, fingerprint, result, created) VALUES (?, ?, ?, ?, ?)",
    [datasetIdValue, operationId, fingerprint, datasetJson({ row_id: rowId, revision: Number(stored.revision), inserted: !existing }, true), now],
  );
  return result;
}

async function datasetDelete(connection: SqlConnection, datasetIdValue: string, columns: Record<string, DatasetColumn>, fields: string[], argumentsValue: Record<string, unknown>, operationId: string, binding: string): Promise<Record<string, unknown>> {
  if (!/^[A-Za-z0-9_.:-]{1,128}$/.test(operationId)) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  const names = Object.keys(argumentsValue).sort().join(",");
  if (names !== "row_id" && names !== "key,value") datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  let target: { key: string | null; row_id: string | null; value: unknown };
  if (names === "row_id") {
    const rowId = argumentsValue.row_id;
    if (typeof rowId !== "string" || rowId.length < 1 || rowId.length > 100) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
    target = { key: null, row_id: rowId, value: null };
  } else {
    const key = argumentsValue.key;
    if (typeof key !== "string") datasetFail("DATASET_UPSERT_KEY_INVALID", { field: String(key) });
    const column = datasetColumn(columns, key);
    const raw = argumentsValue.value;
    if (!column.unique || (raw !== null && typeof raw === "object")) datasetFail("DATASET_UPSERT_KEY_INVALID", { field: key });
    const value = datasetNormalize(column, raw, false);
    if (value === null || value === undefined) datasetFail("DATASET_UPSERT_KEY_INVALID", { field: key });
    target = { key, row_id: null, value };
  }
  const fingerprint = writeFingerprint({ arguments: target, fields, operation: "delete_row" });
  const previous = await connection.get(
    "SELECT fingerprint, result FROM superstep_dataset_receipts WHERE dataset_id = ? AND operation_id = ?",
    [datasetIdValue, operationId],
  );
  if (previous) {
    if (previous.fingerprint !== fingerprint) datasetFail("DATASET_RECEIPT_CONFLICT");
    return storedJson(previous.result, binding);
  }
  let rowId = target.row_id;
  if (target.key !== null) {
    const hit = await connection.get(
      "SELECT row_id FROM superstep_dataset_keys WHERE dataset_id = ? AND field = ? AND digest = ?",
      [datasetIdValue, target.key, datasetDigest(target.value)],
    );
    rowId = hit ? String(hit.row_id) : null;
  }
  const row = rowId === null ? undefined : await connection.get(
    "SELECT id FROM superstep_dataset_rows WHERE dataset_id = ? AND id = ?", [datasetIdValue, rowId],
  );
  // A row that is already gone fails without a receipt.
  if (!row) datasetFail("DATASET_ROW_NOT_FOUND");
  const deleted = String(row.id);
  await connection.run("DELETE FROM superstep_dataset_keys WHERE dataset_id = ? AND row_id = ?", [datasetIdValue, deleted]);
  await connection.run("DELETE FROM superstep_dataset_rows WHERE dataset_id = ? AND id = ?", [datasetIdValue, deleted]);
  const result = { deleted: true, row_id: deleted };
  await connection.run(
    "INSERT INTO superstep_dataset_receipts (dataset_id, operation_id, fingerprint, result, created) VALUES (?, ?, ?, ?, ?)",
    [datasetIdValue, operationId, fingerprint, datasetJson(result, true), Date.now() / 1000],
  );
  return result;
}

async function datasetStandalone(binding: string, backend: string, operation: string, fields: string[], argumentsValue: Record<string, unknown>, operationId?: string): Promise<Record<string, unknown>> {
  const columns = datasetContract(binding).columns;
  const allowed = DATASET_OPERATION_INPUTS[operation];
  if (!allowed || !plainObject(argumentsValue) || Object.keys(argumentsValue).some((key) => !allowed.includes(key)) || (!fields.length && operation !== "insert_row" && operation !== "upsert_row") || new Set(fields).size !== fields.length) {
    datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
  }
  for (const field of fields) datasetColumn(columns, field);
  const [connection, datasetIdValue] = await openDataset(binding, backend, false);
  const write = operation === "insert_row" || operation === "upsert_row" || operation === "delete_row";
  try {
    return await connection.transaction(write, datasetIdValue, async () => {
      await datasetStorageReady(connection, binding);
      if (write) {
        await connection.run("UPDATE superstep_dataset_definitions SET dataset_id = dataset_id WHERE dataset_id = ?", [datasetIdValue]);
        await datasetExpireReceipts(connection, datasetIdValue);
      }
      await datasetSchemasMatch(connection, datasetIdValue, binding);
      if (write) {
        if (operationId === undefined) datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
        if (operation === "delete_row") return datasetDelete(connection, datasetIdValue, columns, fields, argumentsValue, operationId, binding);
        return datasetWrite(connection, datasetIdValue, columns, operation, fields, argumentsValue, operationId, binding);
      }
      if (operation === "aggregate_rows") return datasetAggregate(connection, datasetIdValue, columns, fields, argumentsValue, binding);
      if (operation === "find_rows") return datasetFind(connection, datasetIdValue, columns, fields, argumentsValue, binding);
      if (operation === "get_row") {
        const rowId = argumentsValue.row_id;
        if (Object.keys(argumentsValue).length !== 1 || typeof rowId !== "string" || rowId.length < 1 || rowId.length > 100) {
          datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
        }
        const row = await connection.get(
          'SELECT id, "values" AS payload, revision, created, updated FROM superstep_dataset_rows WHERE dataset_id = ? AND id = ?',
          [datasetIdValue, rowId],
        );
        if (!row) datasetFail("DATASET_ROW_NOT_FOUND");
        return datasetRow(row, fields, binding);
      }
      datasetFail("DATASET_NODE_ARGUMENTS_INVALID");
    });
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("DATASET_")) throw error;
    datasetFail("DATASET_STORAGE_ERROR", { binding });
  } finally {
    await connection.close();
  }
}
'''
