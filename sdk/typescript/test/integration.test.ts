// Live test against a running backend. scripts/sdk_integration.sh (repository root) starts one and sets the variables.
import { describe, expect, it } from 'vitest'
import { AuthenticationError, NotFoundError, Superstep } from '../src/index'

const IT = { baseUrl: process.env.SUPERSTEP_IT_BASE_URL, token: process.env.SUPERSTEP_IT_TOKEN, workflowId: process.env.SUPERSTEP_IT_WORKFLOW_ID }
const input = { message: 'where is my order A100' }

describe.skipIf(!IT.baseUrl || !IT.token || !IT.workflowId)('live backend', () => {
  const client = new Superstep(IT)
  it('run, getRun, runAndWait, sync mode', async () => {
    const started = await client.run(input)
    expect(started.status).toBe('queued'); expect(started.poll_url?.endsWith(started.run_id)).toBe(true)
    const run = await client.wait(started.run_id, { timeoutMs: 60_000, pollIntervalMs: 200 })
    expect(run.status).toBe('ok'); expect(run.final_state?.intent).toBe('order_status'); expect(run.source).toBe('api')
    expect((await client.runAndWait(input, { timeoutMs: 60_000, pollIntervalMs: 200 })).status).toBe('ok')
    expect((await client.run(input, { mode: 'sync' })).status).toBe('ok')
  }, 120_000)
  it('typed errors', async () => {
    await expect(client.getRun('does-not-exist')).rejects.toBeInstanceOf(NotFoundError)
    await expect(new Superstep({ ...IT, token: 'wft_wrong' }).run(input)).rejects.toBeInstanceOf(AuthenticationError)
  })
})
