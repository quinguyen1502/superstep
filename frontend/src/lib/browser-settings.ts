/** Browser/web connection drafts. The backend remains authoritative for network and capability checks. */
import type { ManagedSettings, McpSecretInput } from './mcp'

export type ConnectionErrors = Record<string, string>
export const connectionFieldId = (idp: string, name: string) => `${idp}-${name}`
/** Visual/DOM order so invalid-submit focus matches the form, not Object.keys insertion. */
const CONNECTION_FOCUS_ORDER = [
  'provider', 'browserless_token', 'proxy_mode', 'proxy_server', 'proxy_auth', 'proxy_username', 'proxy_password',
  'allowed_origins', 'profile_name', 'profile_origins', 'profile_state',
  'require_mutating_approval', 'allow_evaluate_js', 'allow_upload', 'allow_download',
  'action_timeout_ms', 'idle_timeout_s', 'lifetime_s', 'max_actions', 'max_pages',
  'enabled_tools', 'search_endpoint', 'search_headers',
] as const
export const firstConnectionError = (errors: ConnectionErrors) =>
  CONNECTION_FOCUS_ORDER.find(name => name in errors) || Object.keys(errors)[0]
export const object = (value: unknown): ManagedSettings => value && typeof value === 'object' && !Array.isArray(value) ? value as ManagedSettings : {}
export const text = (value: unknown, fallback = '') => typeof value === 'string' ? value : fallback
export const lines = (value: unknown): string[] => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
const cleanLines = (value: unknown) => lines(value).map(item => item.trim()).filter(Boolean)
const normalizedLines = (value: unknown) => value === undefined ? [] : Array.isArray(value) && value.every(item => typeof item === 'string') ? cleanLines(value).map(entry => validUrl(entry, { origin: true }) ? new URL(entry).origin : entry) : value
const hasControl = (value: string, spaces = false) => Array.from(value).some(char => char.charCodeAt(0) < (spaces ? 33 : 32) || char.charCodeAt(0) === 127)
export const isBrowserAdapter = (adapter: string) => adapter === 'browser' || adapter === 'web'
/** Accepted DEC-0085 defaults: required whitelist, mutating approval OFF, Browserless = self-hosted controller. */
export const browserDefaults = (): ManagedSettings => ({
  provider: 'local', proxy: { mode: 'direct', auth: 'none' }, allowed_origins: [],
  action_timeout_ms: 30000, idle_timeout_s: 1800, lifetime_s: 3600, max_actions: 40, max_pages: 4,
  require_mutating_approval: false, allow_evaluate_js: false, allow_upload: false, allow_download: false, stealth: false,
})
export const webDefaults = (): ManagedSettings => ({ enabled_tools: ['fetch'], allowed_origins: [] })

export function normalizeConnection(adapter: string, draft: ManagedSettings): ManagedSettings {
  if (!isBrowserAdapter(adapter)) return draft
  const result = { ...draft, allowed_origins: normalizedLines(draft.allowed_origins) }
  if (adapter === 'web') return result
  const profile = object(draft.profile)
  return { ...result, ...(draft.profile ? { profile: { ...profile, origins: normalizedLines(profile.origins) } } : {}),
    proxy: text(object(draft.proxy).mode, 'direct') === 'custom' ? object(draft.proxy) : { mode: text(object(draft.proxy).mode, 'direct'), auth: 'none' } }
}

export function activeConnectionSecrets(adapter: string, settings: ManagedSettings, secrets: McpSecretInput[]) {
  if (!isBrowserAdapter(adapter)) return secrets
  const allowed = new Set<string>()
  if (adapter === 'web') { if (settings.search) allowed.add('search_headers') }
  else {
    if (text(settings.provider, 'local') === 'browserless') allowed.add('browserless_token')
    const proxy = object(settings.proxy)
    if (proxy.mode === 'custom' && proxy.auth === 'basic') { allowed.add('proxy_username'); allowed.add('proxy_password') }
    if (settings.profile) allowed.add('profile_state')
  }
  return secrets.filter(secret => allowed.has(secret.name))
}

function validUrl(value: string, { origin = false, https = false, proxy = false } = {}) {
  try {
    if (!value || hasControl(value, true) || value.includes('\\')) return false
    const url = new URL(value)
    if (!(proxy ? url.protocol === 'http:' : https ? url.protocol === 'https:' : ['http:', 'https:'].includes(url.protocol)) || !url.hostname || url.hostname.includes('*') || url.username || url.password) return false
    if (url.port && !(Number(url.port) >= 1 && Number(url.port) <= 65535)) return false
    return !(origin || proxy) || ((!url.pathname || url.pathname === '/') && !url.search && !url.hash)
  } catch { return false }
}

export function connectionErrors(adapter: string, draft: ManagedSettings, secrets: McpSecretInput[], scope: string): ConnectionErrors {
  if (!isBrowserAdapter(adapter)) return {}
  const settings = normalizeConnection(adapter, draft), errors: ConnectionErrors = {}
  const add = (field: string, key: string) => { errors[field] = `browserSettings.errors.${key}` }
  const secret = (name: string) => secrets.find(item => item.name === name)
  const hasSecret = (name: string) => { const value = secret(name); return !!value && (value.stored || !!value.value) }
  const checkOrigins = (value: unknown, field: string, max: number, https = false, required = false) => {
    const entries = cleanLines(value)
    if (!Array.isArray(value) || value.some(item => typeof item !== 'string') || (required && !entries.length) || entries.length > max || new Set(entries).size !== entries.length || entries.some(entry => !validUrl(entry, { origin: true, https }))) add(field, https ? 'httpsOrigins' : 'origins')
  }
  // Browser connections require a non-empty origin whitelist (DEC-0085). Web discovery may leave it empty.
  checkOrigins(settings.allowed_origins, 'allowed_origins', 50, false, adapter === 'browser')
  if (settings.version !== undefined && settings.version !== 1) add('provider', 'unsupported')
  if (adapter === 'web') {
    const enabled = lines(settings.enabled_tools ?? ['fetch'])
    if (enabled.some(name => !['search', 'fetch'].includes(name))) add('enabled_tools', 'unsupported')
    const search = object(settings.search)
    if (enabled.includes('search') && !settings.search) add('search_endpoint', 'searchEndpoint')
    if (settings.search && (search.provider !== 'searxng' || !validUrl(text(search.endpoint), { https: true }) || /[?#]/.test(text(search.endpoint)))) add('search_endpoint', 'searchEndpoint')
    const headers = secret('search_headers')
    if (headers?.value) {
      try {
        const values: unknown = JSON.parse(headers.value)
        if (!values || typeof values !== 'object' || Array.isArray(values) || headers.value.length > 4096 || Object.keys(values).length > 20 || Object.values(values).some(value => typeof value !== 'string' || !value || hasControl(value))) throw new Error()
      } catch { add('search_headers', 'headers') }
    }
    return errors
  }
  const provider = text(settings.provider, 'local'), proxy = object(settings.proxy)
  if (!['local', 'browserless'].includes(provider) || settings.stealth === true) add('provider', 'unsupported')
  if (provider === 'browserless') {
    const token = secret('browserless_token')
    if (!hasSecret('browserless_token') || (token?.value && (!/^[\x21-\x7e]{8,4096}$/.test(token.value)))) add('browserless_token', 'token')
  }
  if (!['direct', 'operator_default', 'custom'].includes(text(proxy.mode, 'direct'))) add('proxy_mode', 'unsupported')
  if (proxy.mode === 'custom') {
    if (!validUrl(text(proxy.server), { proxy: true })) add('proxy_server', 'proxy')
    if (!['none', 'basic'].includes(text(proxy.auth, 'none'))) add('proxy_auth', 'unsupported')
    if (proxy.auth === 'basic') for (const name of ['proxy_username', 'proxy_password']) {
      if (!hasSecret(name) || (secret(name)?.value && (secret(name)!.value.length > 4096 || hasControl(secret(name)!.value)))) add(name, 'requiredSecret')
    }
  }
  if (settings.profile) {
    const profile = object(settings.profile)
    if (scope !== 'user') add('profile_name', 'personalProfile')
    else if (!/^[A-Za-z0-9_.:-]{1,128}$/.test(text(profile.name))) add('profile_name', 'profileName')
    checkOrigins(profile.origins, 'profile_origins', 20, true, true)
    const state = secret('profile_state')
    if (!hasSecret('profile_state')) add('profile_state', 'requiredSecret')
    else if (state?.value) {
      try { const value: unknown = JSON.parse(state.value); if (new TextEncoder().encode(state.value).length > 65536 || !value || typeof value !== 'object' || Array.isArray(value)) throw new Error() }
      catch { add('profile_state', 'profileState') }
    }
  }
  const bounds = {
    action_timeout_ms: [1000, 60000, 30000],
    idle_timeout_s: [60, 7200, 1800],
    lifetime_s: [120, 14400, 3600],
    max_actions: [1, 200, 40],
    max_pages: [1, 20, 4],
  } as const
  for (const [field, [min, max, fallback]] of Object.entries(bounds)) {
    const value = settings[field] === undefined ? fallback : settings[field]
    if (typeof value !== 'number' || !Number.isInteger(value) || value < min || value > max) add(field, 'resource')
  }
  if (typeof settings.idle_timeout_s === 'number' && typeof settings.lifetime_s === 'number' && settings.idle_timeout_s > settings.lifetime_s) add('idle_timeout_s', 'idleLifetime')
  for (const flag of ['require_mutating_approval', 'allow_evaluate_js', 'allow_upload', 'allow_download'] as const) {
    if (settings[flag] !== undefined && typeof settings[flag] !== 'boolean') add(flag, 'unsupported')
  }
  if (settings.profile && cleanLines(settings.allowed_origins).length && cleanLines(object(settings.profile).origins).some(origin => !cleanLines(settings.allowed_origins).includes(origin))) add('profile_origins', 'profileScope')
  return errors
}
