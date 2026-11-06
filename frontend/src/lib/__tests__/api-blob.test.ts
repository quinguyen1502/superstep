import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from '../api'

afterEach(() => vi.unstubAllGlobals())
describe('protected binary API responses', () => {
  it('uses the shared client and does not parse image bytes as an envelope', async () => {
    const bytes = new Blob(['synthetic-image'], { type: 'image/png' }), json = vi.fn()
    const fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, blob: async () => bytes, json })
    vi.stubGlobal('fetch', fetch)
    expect(await api<Blob>('/api/browser/artifacts/fixture', { response: 'blob' })).toBe(bytes)
    expect(fetch.mock.calls[0][1].headers['X-Requested-With']).toBe('studio')
    expect(json).not.toHaveBeenCalled()
  })
  it('keeps shared translated errors when a capture is denied or expired', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({ success: false, error: { code: 'BROWSER_ARTIFACT_NOT_FOUND', message: 'Browser artifact not found' } }) }))
    const error = await api('/api/browser/artifacts/fixture', { response: 'blob' }).catch(error => error)
    expect(error).toBeInstanceOf(ApiError); expect(error.code).toBe('BROWSER_ARTIFACT_NOT_FOUND')
  })
})
