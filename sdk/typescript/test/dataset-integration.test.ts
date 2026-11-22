import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { DatasetClient } from '../src/index'
import type { DatasetColumn } from '../src/index'

const baseUrl = process.env.SUPERSTEP_IT_BASE_URL
const file = process.env.SUPERSTEP_IT_CHAT_CONFIG
const fixtures = file ? JSON.parse(readFileSync(file, 'utf8')) : undefined
const columns: DatasetColumn[] = [
  { key: 'ticket', kind: 'text', unique: true, required: true },
  { key: 'score', kind: 'number' },
]

describe.skipIf(!baseUrl || !fixtures)('live Dataset SDK', () => {
  it('executes all operations, replays a committed write after network loss, and respects scope', async () => {
    const api = async (method: string, path: string, data?: unknown) => {
      const response = await fetch(baseUrl + path, {
        method, headers: { Authorization: `Bearer ${fixtures.owner}`, 'Content-Type': 'application/json' },
        body: data === undefined ? undefined : JSON.stringify(data),
      })
      expect(response.ok).toBe(true)
      return (await response.json()).data
    }
    const dataset = await api('POST', '/api/datasets', {
      name: 'SDK TypeScript', columns: columns.map(column => ({ ...column, label: column.key })),
    })
    const base = `/api/datasets/${dataset.id}`
    const issued = await api('POST', base + '/access/tokens', { name: 'All', permission: 'read_write', allow_delete: true })
    const writer = await api('POST', base + '/access/tokens', { name: 'Write', permission: 'write' })
    const options = { baseUrl: baseUrl!, datasetId: dataset.id, token: issued.token, columns }
    const bodies: (BodyInit | null | undefined)[] = []
    const client = new DatasetClient({ ...options, fetch: async (url, init) => {
      const response = await fetch(url, init)
      bodies.push(init?.body)
      if (bodies.length === 1) {
        expect(response.ok).toBe(true)
        await response.text()
        throw new TypeError('simulated interruption after the server committed')
      }
      return response
    } })
    const write = new DatasetClient({ ...options, token: writer.token })
    const drift = new DatasetClient({ ...options, columns: [columns[0], { key: 'score', kind: 'text' }] })
    const fields = ['ticket', 'score']
    const inserted = await client.insertRow({ ticket: 'T1', score: 2 }, { fields })
    expect(bodies[0]).toBe(bodies[1])
    expect(inserted).toMatchObject({ inserted: true, row: { values: { ticket: 'T1', score: 2 } } })
    const rowId = inserted.row.id
    expect((await client.getRow(rowId, ['score'])).values).toEqual({ score: 2 })
    const result = await client.findRows(fields, {
      filter_tree: { type: 'group', conjunction: 'and', children: [{ type: 'rule', field: 'score', op: 'gte', value: 2 }] },
      sorts: [{ field: 'score' }], limit: 1,
    })
    expect(result.items.map(row => row.id)).toEqual([rowId])
    expect(result.next_offset).toBeNull()
    expect(await client.upsertRow('ticket', { ticket: 'T1', score: 3 }, { fields, operationId: 'example:T1' }))
      .toMatchObject({ inserted: false, row: { id: rowId } })
    expect((await client.aggregateRows(fields, { summaries: { score: 'sum' } })).groups)
      .toEqual([{ group: null, total: 1, values: { score: 3 } }])
    await expect(drift.findRows(fields)).rejects.toMatchObject({ code: 'DATASET_BINDING_SCHEMA_MISMATCH', status: 409 })

    const identity = await write.insertRow({ ticket: 'T2', score: 4 })
    expect(Object.keys(identity.row).sort()).toEqual(['id', 'revision'])
    await expect(write.upsertRow('ticket', { ticket: 'T2' }, { fields: ['score'] })).rejects.toMatchObject({ code: 'DATASET_GRANT_DENIED', status: 403 })
    await expect(write.deleteRow({ row_id: rowId }, fields)).rejects.toMatchObject({ code: 'DATASET_TOKEN_SCOPE', status: 403 })
    expect(await client.deleteRow({ key: 'ticket', value: 'T1' }, fields)).toEqual({ row_id: rowId, deleted: true })
    await api('DELETE', `${base}/access/tokens/${issued.id}`)
    await expect(client.findRows(fields)).rejects.toMatchObject({ code: 'AUTH_TOKEN_INVALID', status: 401 })
  })
})
