import { readFileSync } from 'node:fs'
import { webcrypto } from 'node:crypto'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mintChatToken } from '../src/server'
import * as browserEntry from '../src/index'

const vectors = JSON.parse(readFileSync(new URL('../../fixtures/chat-token-vectors.json', import.meta.url), 'utf8')).vectors
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })
describe('server-only token signing', () => {
  for (const engine of ['WebCrypto', 'Node fallback']) it(`matches backend HS256 vectors with ${engine}`, async () => {
    vi.stubGlobal('crypto', engine === 'WebCrypto' ? webcrypto : undefined)
    for (const vector of vectors) {
      vi.spyOn(Date, 'now').mockReturnValue(vector.issuedAt * 1000)
      expect(await mintChatToken(vector.options)).toBe(vector.token)
    }
  })
  it('does not export signing or secrets through the browser entry', () => {
    expect(browserEntry).not.toHaveProperty('mintChatToken')
  })
  it('bounds claims, rejects malformed JSON and never includes secrets in errors', async () => {
    const base = vectors[0].options
    for (const change of [{ ttl: 0 }, { ttl: 3601 }, { ttl: NaN }, { ttl: 1.5 }, { userId: '' }, { userId: '👩'.repeat(129) },
      { name: 'a'.repeat(81) }, { userId: '\ud800' }, { secret: '' }, { keyId: '☃' }, { slug: '../chat' },
      { meta: [] }, { meta: { value: NaN } }, { meta: { value: undefined } }, { meta: { value: '\ud800' } },
      { meta: { value: 'é'.repeat(512) } }, { meta: { toJSON: () => [] } }]) {
      const error = await mintChatToken({ ...base, ...change }).catch(error => error)
      expect(error).toMatchObject({ code: 'CONFIG_INVALID' })
      expect(String(error)).not.toContain(base.secret)
    }
    await expect(mintChatToken({ ...base, userId: '👩'.repeat(128), ttl: 1 })).resolves.toBeTypeOf('string')
  })
})
