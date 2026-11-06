import { errorText, type ApiErrorBody } from '@/lib/i18n'
// TASK-0045: the JWT lives in an HttpOnly cookie that scripts cannot read. The page keeps only the user and the expiry.
type Session = { expires_at: number; user: { id: string; email: string } }
localStorage.removeItem('token')  // tokens stored by older versions
export const getUser = (): { id: string; email: string } | null => JSON.parse(localStorage.getItem('user') || 'null')
export const wasExpired = () => sessionStorage.getItem('lgs_expired') === '1'
export function setSession(s: Session) { sessionStorage.removeItem('lgs_expired'); localStorage.setItem('session_exp', String(s.expires_at)); localStorage.setItem('user', JSON.stringify(s.user)) }
function clearSession() { localStorage.removeItem('session_exp'); localStorage.removeItem('user') }
export function logout() {
  fetch('/api/auth/logout', { method: 'POST', keepalive: true }).catch(() => {}).finally(() => { clearSession(); sessionStorage.removeItem('lgs_expired'); location.href = '/login' })
}

/** Seconds-since-epoch expiry of the session (the server is authoritative). */
export function sessionExp(): number | null { const n = Number(localStorage.getItem('session_exp')); return n > 0 ? n : null }
export const signedIn = () => { const e = sessionExp(); return !!e && e * 1000 > Date.now() }
/** There was a session in this browser (so a redirect to /login says it expired). */
export const hadSession = () => sessionExp() !== null

export const loginUrl = (expired: boolean, next = location.pathname + location.search) =>
  `/login?${expired ? 'expired=1&' : ''}next=${encodeURIComponent(next)}`
/** Clear session and send the user to /login with an "expired" notice, coming back here afterwards. */
export function sessionExpired() {
  if (location.pathname === '/login') return
  // Flag survives the race with <Protected> re-rendering after the session is cleared.
  clearSession(); sessionStorage.setItem('lgs_expired', '1'); location.href = loginUrl(true)
}
/** Auto-logout exactly when the token expires (call once at app start). */
let timer: number | undefined
export function scheduleExpiry() {
  clearTimeout(timer); const e = sessionExp(); if (!e) return
  const ms = e * 1000 - Date.now()
  // setTimeout overflows above 2^31-1 ms (~24.8 days) and would fire immediately; re-check later instead.
  timer = ms > 2 ** 31 - 1 ? window.setTimeout(scheduleExpiry, 2 ** 31 - 1) : window.setTimeout(sessionExpired, Math.max(0, ms))
}

export class ApiError extends Error {
  status: number; code?: string; details?: any
  constructor(body: ApiErrorBody, status: number) { super(errorText(body)); this.status = status; this.code = body.code; this.details = body.details }
}

/** The one API client: sends the session cookie, unwraps the {success, data, error} envelope, throws ApiError (translated message). */
export async function api<T = any>(path: string, opts: RequestInit & { json?: any; response?: 'blob' } = {}): Promise<T> {
  const headers: Record<string, string> = { 'X-Requested-With': 'studio', ...(opts.headers as any) }  // the server requires it on cookie writes (CSRF)
  if (opts.json !== undefined) { headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(opts.json) }
  let r: Response
  try { r = await fetch(path, { ...opts, headers }) } catch { throw new ApiError({ code: 'NETWORK_ERROR' }, 0) }
  if (opts.response === 'blob' && r.ok) return await r.blob() as T
  const body = await r.json().catch(() => null)
  if (r.status === 401 && !path.startsWith('/api/auth')) { sessionExpired(); throw new ApiError(body?.error ?? { code: 'AUTH_TOKEN_EXPIRED' }, 401) }
  // deactivated by an admin (TASK-0014): drop the session; signing in again shows the reason
  if (body?.error?.code === 'AUTH_ACCOUNT_DISABLED' && !path.startsWith('/api/auth')) { clearSession(); location.href = '/login' }
  if (!body?.success) throw new ApiError(body?.error ?? { code: r.status >= 500 ? 'INTERNAL_ERROR' : 'HTTP_ERROR', message: `HTTP ${r.status}` }, r.status)
  return body.data
}
/** Same-origin socket URL: the browser sends the session cookie with the handshake. */
export const wsUrl = (p: string) => `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${p}`
