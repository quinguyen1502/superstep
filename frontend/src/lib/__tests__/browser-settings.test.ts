import { describe, expect, it } from 'vitest'
import { activeConnectionSecrets, browserDefaults, connectionErrors, normalizeConnection, webDefaults } from '../browser-settings'

const stored = (name: string) => ({ name, value: '', stored: true })
const withOrigins = (patch: Record<string, unknown> = {}) => ({ ...browserDefaults(), allowed_origins: ['https://example.org'], ...patch })
describe('browser connection drafts', () => {
  it('requires a non-empty origin whitelist and canonicalises origins', () => {
    expect(normalizeConnection('browser', { allowed_origins: [' ', ' HTTPS://EXAMPLE.org:443/ '] }).allowed_origins).toEqual(['https://example.org'])
    expect(connectionErrors('browser', { ...browserDefaults(), allowed_origins: [] }, [], 'user')).toHaveProperty('allowed_origins')
    for (const allowed_origins of ['https://example.org', [42], ['https://example.org/private']]) {
      expect(connectionErrors('browser', { ...browserDefaults(), allowed_origins }, [], 'user')).toHaveProperty('allowed_origins')
    }
    expect(connectionErrors('browser', withOrigins({ allowed_origins: ['https://example.org', 'https://EXAMPLE.org/'] }), [], 'user')).toHaveProperty('allowed_origins')
    expect(connectionErrors('browser', withOrigins(), [], 'user')).toEqual({})
  })
  it('keeps stored browserless/basic/profile secrets without re-entry', () => {
    const settings = withOrigins({ provider: 'browserless', proxy: { mode: 'custom', auth: 'basic', server: 'http://proxy.example.org:3128' }, profile: { name: 'personal', origins: ['https://example.org'] } })
    const secrets = ['browserless_token', 'proxy_username', 'proxy_password', 'profile_state'].map(stored)
    expect(connectionErrors('browser', settings, secrets, 'user')).toEqual({})
    expect(connectionErrors('browser', settings, secrets.filter(secret => secret.name !== 'proxy_password'), 'user')).toHaveProperty('proxy_password')
    expect(activeConnectionSecrets('browser', browserDefaults(), secrets)).toEqual([])
    expect(activeConnectionSecrets('browser', withOrigins({ provider: 'browserless' }), secrets).map(s => s.name)).toEqual(['browserless_token'])
  })
  it('rejects unsupported proxy transports and secret injection', () => {
    for (const server of ['socks5://proxy.example.org:1080', 'https://proxy.example.org', 'http://user:pass@proxy.example.org', 'http://proxy.example.org/path']) {
      expect(connectionErrors('browser', withOrigins({ proxy: { mode: 'custom', server } }), [], 'user')).toHaveProperty('proxy_server')
    }
    expect(connectionErrors('browser', withOrigins({ provider: 'browserless' }), [{ name: 'browserless_token', value: 'bad token', stored: false }], 'user')).toHaveProperty('browserless_token')
    expect(connectionErrors('browser', withOrigins({ stealth: true }), [], 'user')).toHaveProperty('provider')
    expect(connectionErrors('browser', withOrigins({ provider: 'controlled_remote' }), [], 'user')).toHaveProperty('provider')
  })
  it('checks profile scope and coupled lifetime limits', () => {
    const settings = withOrigins({ allowed_origins: ['https://a.example.org'], profile: { name: 'personal', origins: ['https://b.example.org'] }, idle_timeout_s: 1800, lifetime_s: 600 })
    expect(connectionErrors('browser', settings, [stored('profile_state')], 'org')).toMatchObject({ profile_name: 'browserSettings.errors.personalProfile', profile_origins: 'browserSettings.errors.profileScope', idle_timeout_s: 'browserSettings.errors.idleLifetime' })
    expect(connectionErrors('browser', withOrigins({ max_actions: 1.5, action_timeout_ms: 999 }), [], 'user')).toHaveProperty('max_actions')
    expect(connectionErrors('browser', withOrigins({ profile: { name: 'p', origins: ['http://example.org'] } }), [stored('profile_state')], 'user')).toHaveProperty('profile_origins')
  })
  it('defaults mutating approval and advanced tools to off', () => {
    const defaults = browserDefaults()
    expect(defaults.require_mutating_approval).toBe(false)
    expect(defaults.allow_evaluate_js).toBe(false)
    expect(defaults.allow_upload).toBe(false)
    expect(defaults.allow_download).toBe(false)
    expect(connectionErrors('browser', withOrigins({ require_mutating_approval: true, allow_evaluate_js: true }), [], 'user')).toEqual({})
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
