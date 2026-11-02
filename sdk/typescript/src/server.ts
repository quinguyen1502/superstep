// Server/edge only. Never import this entry into a browser or mobile application holding an app key.
import { ConfigError } from './errors.js'

export interface MintChatTokenOptions {
  keyId: string
  secret: string
  slug: string
  userId: string
  name?: string
  meta?: Record<string, unknown>
  /** Token lifetime in seconds: 1..3600; default 600. */
  ttl?: number
}

function text(value: string, name: string, maximum: number, empty = false): void {
  if (typeof value !== 'string') throw invalid(name)
  let count = 0
  for (const char of value) {
    const point = char.codePointAt(0)!
    if (point >= 0xd800 && point <= 0xdfff) throw invalid(name)
    count++
  }
  if ((!empty && !count) || count > maximum) throw invalid(name)
}
const invalid = (field: string) => new ConfigError(`Invalid chat token ${field}`, { code: 'CONFIG_INVALID' })
const encode = (bytes: Uint8Array): string => {
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_')
}
const encoder = new TextEncoder()
const part = (value: unknown) => encode(encoder.encode(JSON.stringify(value)))

/** Mint after authenticating the user in your own backend. The secret is the app key's literal UTF-8 value. */
export async function mintChatToken(options: MintChatTokenOptions): Promise<string> {
  const { keyId, secret, slug, userId, name = '', ttl = 600, meta } = options
  text(keyId, 'keyId', 128); text(secret, 'secret', 8192); text(slug, 'slug', 200); text(userId, 'userId', 128); text(name, 'name', 80, true)
  if (!/^[\x21-\x7e]+$/.test(keyId) || !/^[a-zA-Z0-9_-]+$/.test(slug)) throw invalid('keyId/slug')
  if (!Number.isSafeInteger(ttl) || ttl < 1 || ttl > 3600) throw invalid('ttl')
  let cleanMeta: Record<string, unknown> | undefined
  if (meta !== undefined) {
    if (!meta || typeof meta !== 'object' || Array.isArray(meta)) throw invalid('meta')
    try {
      const encoded = JSON.stringify(meta, (key, value) => {
        text(key, 'meta', 1024, true)
        if (['undefined', 'function', 'symbol', 'bigint'].includes(typeof value) || (typeof value === 'number' && !Number.isFinite(value))) throw invalid('meta')
        if (typeof value === 'string') text(value, 'meta', 1024, true)
        return value
      })
      if (encoder.encode(encoded).length > 1024) throw invalid('meta')
      cleanMeta = JSON.parse(encoded) as Record<string, unknown>
      if (!cleanMeta || typeof cleanMeta !== 'object' || Array.isArray(cleanMeta)) throw invalid('meta')
    } catch { throw invalid('meta') }
  }
  const now = Math.floor(Date.now() / 1000)
  const unsigned = part({ alg: 'HS256', typ: 'JWT', kid: keyId }) + '.' + part({ iss: keyId, aud: `superstep-chat:${slug}`,
    sub: userId, name, iat: now, exp: now + ttl, ...(cleanMeta !== undefined ? { meta: cleanMeta } : {}) })
  let subtle = globalThis.crypto?.subtle
  if (!subtle) {
    // The variable import keeps Node built-ins out of edge bundles when Web Crypto is available.
    const module = 'node:crypto'
    try { subtle = (await import(module)).webcrypto.subtle as SubtleCrypto } catch { throw new ConfigError('No HMAC crypto available in this server runtime', { code: 'CONFIG_MISSING' }) }
  }
  const key = await subtle.importKey('raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
  return unsigned + '.' + encode(new Uint8Array(await subtle.sign('HMAC', key, encoder.encode(unsigned))))
}
