/** Bridge v1. Tokens travel only between the exact parent/frame pair, never URLs or public events. */
export const MSG = { ready: 'superstep-chat:ready', token: 'superstep-chat:token', save: 'superstep-chat:save',
  configure: 'superstep-chat:configure', identity: 'superstep-chat:identity', request: 'superstep-chat:token-request',
  response: 'superstep-chat:token-response', event: 'superstep-chat:event', ack: 'superstep-chat:ack' } as const
export const EVENTS = ['ready', 'open', 'close', 'message', 'answer', 'error'] as const
export type WidgetEvent = typeof EVENTS[number]
export type TokenProvider = string | (() => string | Promise<string>)
export type Appearance = { color?: string; logo?: string; language?: 'en' | 'vi'; position?: 'left' | 'right' }
export type InitOptions = Appearance & { slug: string; baseUrl?: string; open?: boolean }
export type WidgetPayload = { slug: string; code?: string; sessionId?: string; turn?: { id: string; role: 'user' | 'assistant'; text: string; status?: string | null } }
export type Handler = (data: Readonly<WidgetPayload>) => void
export interface WidgetAPI {
  init(options: InitOptions): void
  open(): void
  close(): void
  toggle(): void
  identify(token: TokenProvider): Promise<void>
  logout(): Promise<void>
  on(event: WidgetEvent, handler: Handler): () => void
  off(event: WidgetEvent, handler: Handler): void
}
export type Command = [keyof WidgetAPI, ...unknown[]]
export type QueuedWidget = Command[] | { q: Command[] }
declare global { interface Window { Superstep?: WidgetAPI | QueuedWidget } }
export const storageKey = (slug: string) => `superstep-chat:${slug}`
export const visitorToken = (value: unknown): value is string => typeof value === 'string' && /^[0-9a-f]{16}\.[0-9a-f]{32}$/.test(value)
export const userToken = (value: unknown): value is string => typeof value === 'string' && value.length <= 16384 && /^[\w-]+\.[\w-]+\.[\w-]+$/.test(value)
export const channelId = (value: unknown): value is string => typeof value === 'string' && /^[\w-]{1,128}$/.test(value)
export const epochId = (value: unknown): value is number => Number.isSafeInteger(value) && (value as number) >= 0
export const errorCode = (value: unknown) => typeof value === 'string' && /^[A-Z][A-Z0-9_]{0,79}$/.test(value) ? value : 'HTTP_ERROR'
export const bridgeError = (code = 'HTTP_ERROR') => Object.assign(new Error(code), { code })
export function appearance(value: unknown, doc: Document): Appearance {
  if (!value || typeof value !== 'object') return {}
  const v = value as Appearance, result: Appearance = {}
  if (v.language === 'en' || v.language === 'vi') result.language = v.language
  if (v.position === 'left' || v.position === 'right') result.position = v.position
  if (typeof v.color === 'string' && v.color.length <= 120) {
    const probe = doc.createElement('span'); probe.style.color = v.color
    if (v.color === '' || probe.style.color) result.color = v.color
  }
  if (typeof v.logo === 'string' && v.logo.length <= 350000) {
    if (v.logo === '') result.logo = ''
    try { const url = new URL(v.logo); if ((!url.username && !url.password && ['http:', 'https:'].includes(url.protocol)) || /^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(v.logo)) result.logo = v.logo } catch { /* invalid appearance is ignored */ }
  }
  return result
}
export function eventHub() {
  const listeners = new Map<WidgetEvent, Set<Handler>>()
  return {
    on(event: WidgetEvent, handler: Handler) { if (!EVENTS.includes(event) || typeof handler !== 'function') throw bridgeError('VALIDATION_ERROR'); if (!listeners.has(event)) listeners.set(event, new Set()); listeners.get(event)!.add(handler); return () => { listeners.get(event)?.delete(handler) } },
    off(event: WidgetEvent, handler: Handler) { listeners.get(event)?.delete(handler) },
    emit(event: WidgetEvent, data: WidgetPayload) { for (const handler of [...listeners.get(event) ?? []]) { try { handler(Object.freeze(data)) } catch { /* a host subscriber cannot break chat */ } } },
  }
}
export function payload(data: unknown, slug: string): WidgetPayload | null {
  if (!data || typeof data !== 'object') return null
  const v = data as WidgetPayload, result: WidgetPayload = { slug }
  if (v.code) result.code = errorCode(v.code)
  if (typeof v.sessionId === 'string' && /^[\w-]{1,200}$/.test(v.sessionId)) result.sessionId = v.sessionId
  if (v.turn && typeof v.turn.id === 'string' && /^[\w-]{1,200}$/.test(v.turn.id) && ['user','assistant'].includes(v.turn.role) && typeof v.turn.text === 'string') {
    result.turn = { id: v.turn.id, role: v.turn.role, text: v.turn.text.slice(0,100000), ...(typeof v.turn.status === 'string' ? { status: v.turn.status.slice(0,32) } : {}) }
  }
  return result
}

export function failureCode(error: unknown) { try { return errorCode(error && typeof error === 'object' && 'code' in error ? error.code : undefined) } catch { return 'HTTP_ERROR' } }
export async function resolveToken(provider: TokenProvider) {
  let timer: ReturnType<typeof setTimeout> | undefined
  try { const value = await Promise.race([Promise.resolve().then(() => typeof provider === 'function' ? provider() : provider), new Promise<never>((_, reject) => { timer = setTimeout(() => reject(bridgeError()), 10000) })]); if (!userToken(value)) throw bridgeError('CHAT_TOKEN_INVALID'); return value }
  finally { clearTimeout(timer) }
}
