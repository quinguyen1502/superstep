import { test, expect } from '@playwright/test'
import { login, newWorkflow, N } from './helpers'
// TASK-0050: Decision (Jev) node: the question builder edits typed questions, and a run without a TypeSafe key uses the
// offline answers, so a Condition can branch on the choice.
const WF = (name: string) => ({ name,
  state: [{ name: 'message', type: 'string' }, { name: 'intent', type: 'string' }, { name: 'angry', type: 'number' }, { name: 'reply', type: 'string' }],
  nodes: [N('s', 'start', 40),
    N('dec', 'decision', 260, { label: 'Classify', model: 'jev-latest', text: '{{state.message}}', output_field: '',
      questions: [{ id: 'intent', type: 'choice', instructions: 'Which team?', field: 'intent', options: [{ label: 'order', description: 'Delivery' }, { label: 'other', description: '' }] }] }),
    N('route', 'condition', 480, { label: 'Route', field: 'intent', default: 'other' }),
    N('o', 'tool', 700, { label: 'Lookup', mode: 'function', function: 'lookup_order', output_field: 'reply' }, 40), N('e', 'end', 920)],
  edges: [{ id: '1', source: 's', target: 'dec' }, { id: '2', source: 'dec', target: 'route' }, { id: '3', source: 'route', target: 'o', label: 'order' },
    { id: '4', source: 'route', target: 'e', label: 'other' }, { id: '5', source: 'o', target: 'e' }] })

test('decision node: build questions, run offline, branch on the choice', async ({ page }) => {
  const H = await login(page)
  const wid = await newWorkflow(page, H, WF(`Jev ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)
  await page.locator('.react-flow__node[data-id="dec"]').click()
  await expect(page.locator('#decision-settings')).toBeVisible()
  await expect(page.locator('#decision-mock-hint')).toBeVisible()
  await expect(page.locator('#dq-0-opt-0-label')).toHaveValue('order')

  // add a yes/no question that writes a number field
  await page.locator('#dq-add').click()
  await expect(page.locator('#dq-1-id')).toHaveValue('q2')
  await page.locator('#dq-1-type').click(); await page.getByRole('option', { name: 'Có / không' }).click()
  await expect(page.locator('#dq-1-add-option')).toHaveCount(0)
  await page.locator('#dq-1-instructions').click(); await page.keyboard.type('The customer is angry.')
  // the answer fields sit in the Data tab, with every other state field picker (TASK-0121)
  await page.locator('#config-tab-data').click()
  await page.locator('#dq-1-field').click(); await page.getByRole('option', { name: 'angry' }).click()
  await page.locator('#save-btn').click(); await expect(page.locator('#unsaved-badge')).toHaveCount(0)
  const saved = (await (await page.request.get(`/api/workflows/${wid}`, { headers: H })).json()).data
  const qs = saved.nodes.find((n: { id: string }) => n.id === 'dec').data.questions
  expect(qs.map((q: { id: string; type: string; field: string }) => [q.id, q.type, q.field])).toEqual([['intent', 'choice', 'intent'], ['q2', 'noul', 'angry']])
  expect(qs[1].instructions).toBe('The customer is angry.')

  // offline answers pick the option named in the text; the Condition follows it
  await page.locator('#run-tab').click()
  await page.locator('#run-input').fill('{"message": "Where is my order A100?"}')
  await page.locator('#run-btn').click()
  await expect(page.locator('#trace-summary')).toHaveAttribute('data-status', 'ok', { timeout: 30_000 })
  for (const k of ['dec#1', 'route#1', 'o#1']) await expect(page.locator(`.trace-row[data-span="${k}"]`)).toHaveCount(1)
})
