import { afterEach, describe, expect, it, vi } from 'vitest'
import { APIConnectionError, ConfigError, DatasetClient, PermissionDeniedError } from '../src/index'
import type { DatasetClientOptions, DatasetValues } from '../src/index'

const options: Omit<DatasetClientOptions, 'fetch'> = {
  baseUrl: 'https://example.com/studio/', datasetId: 'tickets', token: 'dsat_example',
  columns: [{ key: 'subject', kind: 'text' }],
}

const inserted = { row: { id: 'row', revision: 1 }, inserted: true }
const ok = () => new Response(JSON.stringify({ success: true, data: inserted, error: null }), { status: 200 })
afterEach(() => vi.unstubAllGlobals())

describe('DatasetClient', () => {
  it('retries an interrupted response body with the same serialized request and generates a fresh ID for a new write', async () => {
    const bodies: string[] = []
    const values: DatasetValues = { subject: 'First' }
    const client = new DatasetClient({ ...options, fetch: async (url, request) => {
      expect(url).toBe('https://example.com/studio/api/datasets/tickets/connected')
      expect(request).toMatchObject({ method: 'POST', redirect: 'manual', credentials: 'omit' })
      expect(new Headers(request?.headers).get('Authorization')).toBe('Bearer dsat_example')
      bodies.push(request?.body as string)
      if (bodies.length === 1) {
        values.subject = 'Second'
        return new Response(new ReadableStream({ start(controller) { controller.error(new Error('connection lost')) } }))
      }
      return ok()
    } })
    expect(await client.insertRow(values)).toEqual(inserted)
    expect(await client.insertRow(values)).toEqual(inserted)
    expect(bodies[0]).toBe(bodies[1])
    const [first, _, last] = bodies.map(body => JSON.parse(body))
    expect(first.arguments).toEqual({ values: { subject: 'First' } })
    expect(last.arguments).toEqual({ values: { subject: 'Second' } })
    expect(first.fields).toEqual([])
    expect(first.operation_id).toMatch(/^[0-9a-f-]+$/)
    expect(last.operation_id).not.toBe(first.operation_id)
  })

  it('generates IDs in Node without global Web Crypto', async () => {
    vi.stubGlobal('crypto', undefined)
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValueOnce(ok())
    await new DatasetClient({ ...options, fetch }).insertRow({ subject: 'Example' })
    expect(JSON.parse(fetch.mock.calls[0][1]?.body as string).operation_id).toMatch(/^[0-9a-f-]+$/)
  })

  it('retries once for a transient status and keeps the server code and details', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>()
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ success: false, error: {
        code: 'DATASET_TOKEN_SCOPE', message: 'Denied', details: { operation: 'delete_row' },
      } }), { status: 403 }))
    const client = new DatasetClient({ ...options, fetch })
    const result = client.deleteRow({ key: 'subject', value: 'Example' }, ['subject'], { operationId: 'job:delete' })
    await expect(result).rejects.toBeInstanceOf(PermissionDeniedError)
    await expect(result).rejects.toMatchObject({ code: 'DATASET_TOKEN_SCOPE', status: 403, details: { operation: 'delete_row' } })
    const [first, second] = fetch.mock.calls.map(([, request]) => request?.body)
    expect(first).toBe(second)
    expect(JSON.parse(first as string)).toEqual({
      version: 1, operation: 'delete_row', columns: options.columns, fields: ['subject'],
      arguments: { key: 'subject', value: 'Example' }, operation_id: 'job:delete',
    })
  })

  it('rejects nonfinite values before sending a write', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>()
    const client = new DatasetClient({ ...options, fetch })
    await expect(client.insertRow({ score: NaN }, { operationId: 'test' })).rejects.toThrow(TypeError)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('passes cancellation through without a retry and rejects redirect responses', async () => {
    const controller = new AbortController()
    const aborted = new Error('stopped')
    const fetch = vi.fn<typeof globalThis.fetch>()
      .mockImplementationOnce(async () => { controller.abort(aborted); throw aborted })
      .mockResolvedValueOnce(new Response(null, { status: 307, headers: { Location: 'https://elsewhere.example' } }))
    const client = new DatasetClient({ ...options, fetch })
    await expect(client.findRows(['subject'], {}, { signal: controller.signal })).rejects.toBe(aborted)
    expect(fetch).toHaveBeenCalledTimes(1)
    await expect(client.findRows(['subject'])).rejects.toBeInstanceOf(APIConnectionError)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it.each([
    { baseUrl: 'https://a:b@example.com' }, { baseUrl: 'file:///tmp' }, { datasetId: '..' },
    { baseUrl: 'https://example.com/?token=bad' }, { token: '' }, { columns: [] },
  ])('rejects invalid connection configuration %j', change => {
    expect(() => new DatasetClient({ ...options, ...change })).toThrow(ConfigError)
  })
})
