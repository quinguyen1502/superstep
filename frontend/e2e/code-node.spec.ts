import { test, expect, type Page } from '@playwright/test'
import { login, N, newWorkflow, signIn } from './helpers'
// TASK-0055: Tool node Code mode in the editor. An admin writes main(state), tests it with the run panel input, saves
// and runs; the trace shows the printed output and a traceback. An editor sees the code read-only.
// Needs Docker and the studio-code:1 image (docker build -t studio-code:1 docker/studio-code); skips otherwise.
const UPPER = 'def main(state):\n    print("got", state["message"])\n    return state["message"].upper()\n'
const WF = (name: string) => ({ name, state: [{ name: 'message', type: 'string' }, { name: 'out', type: 'string' }],
  nodes: [N('s', 'start', 40), N('c', 'tool', 300, { label: 'Shout', mode: 'function', function: 'lookup_order', output_field: 'out' }), N('e', 'end', 560)],
  edges: [{ id: '1', source: 's', target: 'c' }, { id: '2', source: 'c', target: 'e' }] })

async function setCode(page: Page, code: string) {
  await page.locator('#code-source').click(); await page.keyboard.press('ControlOrMeta+a'); await page.keyboard.insertText(code)
}
async function runInput(page: Page, json: string) {
  await page.locator('#run-tab').click(); await page.locator('#run-input').fill(json)
}

test('code mode: write, test with sample state, run, traceback, read-only for editors', async ({ page, browser }) => {
  const H = await login(page)
  const rt = (await (await page.request.get('/api/meta/runtime', { headers: H })).json()).data
  test.skip(!rt.available, `Code nodes cannot run here: ${rt.problem || rt.code_runtime}`)
  const wid = await newWorkflow(page, H, WF(`Code ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="c"]').click(); await page.locator('#config-tab-settings').click()
  await page.locator('#tool-mode').click(); await page.getByRole('option', { name: /^Code \(Python/ }).click()
  await expect(page.locator('#code-source')).toContainText('def main(state)')  // starter
  await expect(page.locator('#code-packages')).toContainText('pydantic')
  await setCode(page, UPPER)

  await runInput(page, '{"message": "xin chào", "out": ""}')
  await page.locator('.react-flow__node[data-id="c"]').click()
  await page.locator('#code-test').click()
  await expect(page.locator('#code-test-result')).toContainText('XIN CHÀO', { timeout: 30_000 })
  await expect(page.locator('#code-test-result [data-testid="code-stdout"]')).toHaveText('got xin chào')

  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  const runs = async () => (await (await page.request.get(`/api/workflows/${wid}/runs`, { headers: H })).json()).data
    .sort((a: { started: number }, b: { started: number }) => b.started - a.started)
  expect((await runs())[0].final_state.out).toBe('XIN CHÀO')
  await page.locator('.trace-row[data-span="c#1"]').click()
  await page.locator('#trace-detail').getByRole('tab').nth(1).click()
  await expect(page.locator('#trace-code-output')).toContainText('got xin chào')

  await page.locator('.react-flow__node[data-id="c"]').click()
  await setCode(page, 'def main(state):\n    raise ValueError("bad input")\n')
  await page.locator('#code-test').click()
  await expect(page.locator('#code-test-failure')).toContainText('ValueError: bad input', { timeout: 30_000 })
  await expect(page.locator('#code-test-result [data-testid="code-traceback"]')).toContainText('line 2, in main')
  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'error', { timeout: 30_000 })
  await page.locator('.trace-row[data-span="c#1"]').click()
  await expect(page.locator('#trace-code-output [data-testid="code-traceback"]')).toContainText('ValueError: bad input')

  // an editor the workflow is shared with: code read-only, no test button, still runs
  const email = `code-ed-${Date.now()}@example.com`
  await page.request.post('/api/auth/register', { data: { email, password: 'goodpass1' } })
  await page.request.put(`/api/workflows/${wid}/shares`, { headers: H, data: { email, role: 'editor' } })
  const ctx = await browser.newContext(); const ed = await ctx.newPage()
  await ed.goto('/login'); await signIn(ed, email, 'goodpass1'); await ed.goto(`/workflows/${wid}`)
  await ed.locator('.react-flow__node[data-id="c"]').click()
  await ed.locator('#config-tab-settings').click()
  await expect(ed.locator('#code-read-only')).toBeVisible(); await expect(ed.locator('#code-test')).toHaveCount(0)
  await expect(ed.locator('#code-source')).toHaveAttribute('contenteditable', 'false')
  await ctx.close()
})
