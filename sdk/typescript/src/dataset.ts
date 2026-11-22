import type { components } from './schema.js'
import type { RequestOptions } from './client.js'
import { APIConnectionError, ConfigError } from './errors.js'
import { checkAbort, unwrap } from './transport.js'

type Schemas = components['schemas']
type Operation = Schemas['DatasetConnectedRequest']['operation']
type WriteOperation = Extract<Operation, 'insert_row' | 'upsert_row' | 'delete_row'>

// The generator marks defaulted fields as required. SDK inputs can omit them.
type WithDefaults<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

export type DatasetColumn = WithDefaults<Omit<Schemas['DatasetConnectedColumn'], 'formula' | 'validation_rules'>,
  'required' | 'unique' | 'default'> & {
  formula?: WithDefaults<Schemas['DatasetFormula'], 'version'> | null
  validation_rules?: Partial<Schemas['DatasetColumnRules']> | null
}
export type DatasetFilter = WithDefaults<Schemas['DatasetQueryFilter'], 'value'>
type DatasetFilterRule = WithDefaults<Schemas['DatasetFilterRule'], 'value'>
export type DatasetFilterGroup = Omit<Schemas['DatasetFilterGroup'], 'children'> & {
  children: (DatasetFilterRule | DatasetFilterGroup)[]
}
export type DatasetSort = WithDefaults<Schemas['DatasetSort'], 'descending'>
type DatasetFilters = Partial<Pick<Schemas['DatasetFindArguments'], 'filter_mode' | 'search'>> & {
  filters?: DatasetFilter[]
  filter_tree?: DatasetFilterGroup | null
}
export type DatasetFindArguments = DatasetFilters & Partial<Pick<Schemas['DatasetFindArguments'], 'limit' | 'offset'>> & {
  sorts?: DatasetSort[]
}
export type DatasetAggregateArguments = DatasetFilters &
  WithDefaults<Pick<Schemas['DatasetAggregateQuery'], 'summaries' | 'group_by'>, 'group_by'>
export type DatasetDeleteTarget =
  (Schemas['DatasetRowTarget'] & { key?: never; value?: never }) |
  (Schemas['DatasetUniqueTarget'] & { row_id?: never })
export type DatasetRow = Schemas['DatasetConnectedRow']
export type DatasetRowIdentity = Schemas['DatasetRowIdentity']
export type DatasetValues = DatasetRow['values']
export type DatasetValue = DatasetValues[string]
export type DatasetFindResult = Schemas['DatasetFindResult']
export type DatasetAggregateResult = Schemas['DatasetAggregateResult']
export type DatasetWriteResult = Schemas['DatasetWriteResult']
export type DatasetDeleteResult = Schemas['DatasetDeleteResult']

export interface DatasetClientOptions {
  baseUrl: string
  datasetId: string
  /** A Dataset API token issued for this dataset. */
  token: string
  columns: readonly DatasetColumn[]
  fetch?: typeof fetch
}

export interface DatasetMutationOptions extends RequestOptions {
  /** Reuse this identity with the same arguments and fields when recovering a write. */
  operationId?: string
}

export interface DatasetWriteOptions extends DatasetMutationOptions {
  /** Empty by default for identifiers only. A nonempty list requires read access. */
  fields?: readonly string[]
}

const RETRY_STATUS = new Set([502, 503, 504])

async function newOperationId(): Promise<string> {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  try {
    const module = 'node:crypto'
    return (await import(module)).randomUUID()
  } catch {
    throw new ConfigError('Operation ID generation requires Web Crypto or Node crypto. Pass operationId for this runtime.', { code: 'CONFIG_MISSING' })
  }
}

function connectedUrl(baseUrl: string, datasetId: string): string {
  let base: URL
  try { base = new URL(baseUrl) } catch { throw new ConfigError('Invalid Dataset baseUrl', { code: 'CONFIG_INVALID' }) }
  if (!['https:', 'http:'].includes(base.protocol) || !base.hostname || base.username || base.password || base.search || base.hash) {
    throw new ConfigError('Dataset baseUrl must be an HTTP(S) URL without credentials, query or fragment', { code: 'CONFIG_INVALID' })
  }
  if (!/^[A-Za-z0-9_-]{1,100}$/.test(datasetId)) throw new ConfigError('Invalid datasetId', { code: 'CONFIG_INVALID' })
  return `${base.origin}${base.pathname.replace(/\/+$/, '')}/api/datasets/${datasetId}/connected`
}

/** A client for one Dataset Connected v1 binding. */
export class DatasetClient {
  private readonly url: string
  private readonly columns: readonly DatasetColumn[]
  private readonly fetchImpl: typeof fetch
  readonly #token: string

  constructor(options: DatasetClientOptions) {
    if (!options.token || !options.columns?.length) {
      throw new ConfigError('Dataset clients require a token and column binding', { code: 'CONFIG_MISSING' })
    }
    this.url = connectedUrl(options.baseUrl, options.datasetId)
    this.columns = [...options.columns]
    this.#token = options.token
    const fetchImpl = (options.fetch ?? globalThis.fetch)?.bind(globalThis)
    if (!fetchImpl) throw new ConfigError('No fetch available: pass options.fetch', { code: 'CONFIG_MISSING' })
    this.fetchImpl = fetchImpl
  }

  findRows(fields: readonly string[], args: DatasetFindArguments = {}, options: RequestOptions = {}): Promise<DatasetFindResult> {
    return this.send('find_rows', fields, args, options.signal)
  }

  getRow(rowId: string, fields: readonly string[], options: RequestOptions = {}): Promise<DatasetRow> {
    return this.send('get_row', fields, { row_id: rowId }, options.signal)
  }

  aggregateRows(fields: readonly string[], args: DatasetAggregateArguments, options: RequestOptions = {}): Promise<DatasetAggregateResult> {
    return this.send('aggregate_rows', fields, args, options.signal)
  }

  insertRow(values: DatasetValues, options: DatasetWriteOptions = {}): Promise<DatasetWriteResult> {
    return this.write('insert_row', options.fields ?? [], { values }, options)
  }

  upsertRow(key: string, values: DatasetValues, options: DatasetWriteOptions = {}): Promise<DatasetWriteResult> {
    return this.write('upsert_row', options.fields ?? [], { key, values }, options)
  }

  deleteRow(target: DatasetDeleteTarget, fields: readonly string[], options: DatasetMutationOptions = {}): Promise<DatasetDeleteResult> {
    return this.write('delete_row', fields, target, options)
  }

  private async write<T>(operation: WriteOperation, fields: readonly string[], args: object, options: DatasetMutationOptions): Promise<T> {
    checkAbort(options.signal)
    const operationId = options.operationId ?? await newOperationId()
    return this.send(operation, fields, args, options.signal, operationId)
  }

  private async send<T>(operation: Operation, fields: readonly string[], args: object, signal?: AbortSignal, operationId?: string): Promise<T> {
    // Serialize once so a retry uses the same arguments and receipt identity.
    const body = JSON.stringify({ version: 1, operation, columns: this.columns, fields, arguments: args, operation_id: operationId },
      (_, value: unknown) => {
        if (typeof value === 'number' && !Number.isFinite(value)) throw new TypeError('Dataset requests require finite numbers')
        return value
      })
    const headers = { Authorization: `Bearer ${this.#token}`, Accept: 'application/json', 'Content-Type': 'application/json' }
    const request: RequestInit = { method: 'POST', body, headers, signal, redirect: 'manual', credentials: 'omit' }
    for (let attempt = 0; ; attempt++) {
      checkAbort(signal)
      let response: Response
      let text: string
      try {
        response = await this.fetchImpl(this.url, request)
        text = await response.text()
      } catch (error) {
        if (signal?.aborted) throw error
        if (!attempt) continue
        throw new APIConnectionError(error instanceof Error ? error.message : String(error), { code: 'CONNECTION_ERROR' })
      }
      if (!attempt && RETRY_STATUS.has(response.status)) continue
      let payload: Parameters<typeof unwrap>[1] = null
      try { payload = JSON.parse(text) } catch { /* The shared envelope reports invalid JSON. */ }
      return unwrap<T>(response, payload)
    }
  }
}
