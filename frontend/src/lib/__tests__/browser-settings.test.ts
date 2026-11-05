import { describe, expect, it } from 'vitest'
import { activeConnectionSecrets, browserDefaults, connectionErrors, normalizeConnection, webDefaults } from '../browser-settings'

const stored = (name: string) => ({ name, value: '', stored: true })
describe('browser connection drafts', () => {
  it('canonicalises origins without silently dropping malformed policy', () => {
    expect(normalizeConnection('browser', { allowed_origins: [' ', ' HTTPS://EXAMPLE.org:443/ '] }).allowed_origins).toEqual(['https://example.org'])
    for (const allowed_origins of ['https://example.org', [42], ['https://example.org/private']]) {
      expect(connectionErrors('browser', { allowed_origins }, [], 'user')).toHaveProperty('allowed_origins')
    }
    expect(connectionErrors('browser', { allowed_origins: ['https://example.org', 'https://EXAMPLE.org/'] }, [], 'user')).toHaveProperty('allowed_origins')
  })
  it('keeps stored remote/basic/profile secrets without re-entry', () => {
    const settings = { ...browserDefaults(), provider: 'controlled_remote', proxy: { mode: 'custom', auth: 'basic', server: 'http://proxy.example.org:3128' }, profile: { name: 'personal', origins: ['https://example.org'] } }
    const secrets = ['remote_endpoint', 'remote_token', 'proxy_username', 'proxy_password', 'profile_state'].map(stored)
    expect(connectionErrors('browser', settings, secrets, 'user')).toEqual({})
    expect(connectionErrors('browser', settings, secrets.filter(secret => secret.name !== 'proxy_password'), 'user')).toHaveProperty('proxy_password')
    expect(activeConnectionSecrets('browser', browserDefaults(), secrets)).toEqual([])
  })
  it('rejects unsupported proxy and controller transports and secret injection', () => {
    for (const server of ['socks5://proxy.example.org:1080', 'https://proxy.example.org', 'http://user:pass@proxy.example.org', 'http://proxy.example.org/path']) {
      expect(connectionErrors('browser', { proxy: { mode: 'custom', server } }, [], 'user')).toHaveProperty('proxy_server')
    }
    expect(connectionErrors('browser', { provider: 'controlled_remote' }, [{ name: 'remote_endpoint', value: 'wss://controller.example.org', stored: false }, { name: 'remote_token', value: 'a'.repeat(32), stored: false }], 'user')).toHaveProperty('remote_endpoint')
    expect(connectionErrors('browser', { stealth: true }, [], 'user')).toHaveProperty('provider')
  })
  it('checks profile scope and coupled lifetime limits', () => {
    const settings = { allowed_origins: ['https://a.example.org'], profile: { name: 'personal', origins: ['https://b.example.org'] }, idle_timeout_s: 120, lifetime_s: 60 }
    expect(connectionErrors('browser', settings, [stored('profile_state')], 'org')).toMatchObject({ profile_name: 'browserSettings.errors.personalProfile', profile_origins: 'browserSettings.errors.profileScope', idle_timeout_s: 'browserSettings.errors.idleLifetime' })
    expect(connectionErrors('browser', { max_actions: 1.5, action_timeout_ms: 999 }, [], 'user')).toHaveProperty('max_actions')
    expect(connectionErrors('browser', { profile: { name: 'p', origins: ['http://example.org'] } }, [stored('profile_state')], 'user')).toHaveProperty('profile_origins')
  })
  it('preserves provider/proxy draft values but submits only selected authority', () => {
    const draft = { proxy: { mode: 'direct', auth: 'basic', server: 'http://proxy.example.org' } }
    expect(normalizeConnection('browser', draft).proxy).toEqual({ mode: 'direct', auth: 'none' })
    expect(draft.proxy.auth).toBe('basic')
    expect(activeConnectionSecrets('web', webDefaults(), [stored('profile_state'), stored('proxy_password')])).toEqual([])
  })
  it('requires explicit search setup and validates secret JSON without browser inheritance', () => {
    expect(connectionErrors('web', { enabled_tools: ['search'] }, [], 'user')).toHaveProperty('search_endpoint')
    const settings = { ...webDefaults(), enabled_tools: ['search', 'fetch'], search: { provider: 'searxng', endpoint: 'https://search.example.org/search' } }
    expect(connectionErrors('web', settings, [stored('search_headers')], 'user')).toEqual({})
    for (const value of ['[]', '{"Authorization":123}', '{"Authorization":"a\\nb"}']) {
      expect(connectionErrors('web', settings, [{ name: 'search_headers', value, stored: false }], 'user')).toHaveProperty('search_headers')
    }
    expect(connectionErrors('web', { ...webDefaults(), enabled_tools: [] }, [], 'user')).toEqual({})
  })
})
