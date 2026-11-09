import { expect, type Page } from '@playwright/test'
import { vt } from './catalog'
/** Shared e2e helpers for the Phase 5 editor specs. */
export async function login(page: Page, email = 'admin@example.com', password = 'admin123') {
  await page.goto('/login'); await page.getByLabel('Email').fill(email); await page.getByLabel(vt('auth.password'), { exact: true }).fill(password)
  await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
  return { Authorization: `Bearer ${await apiToken(page, email, password)}` }
}
/** A Bearer token for API calls from a spec. The browser holds the session in an HttpOnly cookie, so scripts cannot read it. */
export async function apiToken(page: Page, email = 'admin@example.com', password = 'admin123'): Promise<string> {
  return (await (await page.request.post('/api/auth/login', { data: { email, password } })).json()).data.token
}
/** Sign the page in without the form: the cookie (page.request shares the browser's jar) plus the page's session record.
 * The page must already be on the app's origin. Returns a Bearer token for API calls. */
export async function signIn(page: Page, email: string, password: string): Promise<string> {
  const s = (await (await page.request.post('/api/auth/login', { data: { email, password } })).json()).data
  await page.evaluate(([exp, u]) => { localStorage.setItem('session_exp', String(exp)); localStorage.setItem('user', JSON.stringify(u)) }, [s.expires_at, s.user] as const)
  return s.token
}
export const N = (id: string, type: string, x: number, data: Record<string, unknown> = {}, y = 120) => ({ id, type, position: { x, y }, data: { label: id, ...data } })
export const SIMPLE = (name: string) => ({ name, state: [{ name: 'message', type: 'string' }, { name: 'answer', type: 'string' }],
  nodes: [N('start', 'start', 40), N('reply', 'llm', 300, { label: 'Reply', model: 'gpt-4o-mini', prompt: 'Answer {{state.message}}', output_field: 'answer' }), N('end', 'end', 560)],
  edges: [{ id: 'e1', source: 'start', target: 'reply' }, { id: 'e2', source: 'reply', target: 'end' }] })
export async function newWorkflow(page: Page, H: Record<string, string>, data: unknown) {
  return (await (await page.request.post('/api/workflows', { headers: H, data })).json()).data.id as string
}
