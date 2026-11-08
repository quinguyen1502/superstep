export interface HostUser { id: string; name: string }
export interface HostSession {
  user: HostUser | null
  config: { baseUrl: string; slug: string }
}

const COOKIE = 'superstep_chat_host'

interface Envelope<T> { success: boolean; data: T | null; error: { message?: string } | null }

/** Loopback client for examples/chat-host. The app key stays on that server. */
export function createHostClient(origin: string) {
  let cookie = ''
  const headers = (json: boolean) => ({
    Accept: 'application/json',
    Origin: origin,
    ...(cookie ? { Cookie: cookie } : {}),
    ...(json ? { 'Content-Type': 'application/json' } : {}),
  })
  const remember = (response: Response) => {
    const raw = response.headers.get('set-cookie') ?? ''
    const match = raw.match(new RegExp(`${COOKIE}=([^;]+)`))
    if (match?.[1]) cookie = `${COOKIE}=${match[1]}`
    return Boolean(match?.[1])
  }
  async function call<T>(path: string, method: string, body?: unknown): Promise<T> {
    const response = await fetch(`${origin}${path}`, {
      method,
      headers: headers(body !== undefined),
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    const saved = remember(response)
    const payload = await response.json() as Envelope<T>
    if (!response.ok || !payload.success || payload.data === null) {
      throw new Error(payload.error?.message || `Host request failed (${response.status})`)
    }
    if (method === 'POST' && path === '/api/auth/login' && !saved) {
      throw new Error('COOKIE')
    }
    return payload.data
  }
  return {
    session: () => call<HostSession>('/api/auth/session', 'GET'),
    login: (persona: 'lan' | 'minh') => call<HostSession>('/api/auth/login', 'POST', { persona }),
    logout: () => call<{ ok: boolean }>('/api/auth/logout', 'POST'),
    token: async () => (await call<{ token: string }>('/api/auth/chat-token', 'POST')).token,
    hasCookie: () => cookie.length > 0,
  }
}
