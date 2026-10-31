import { test, expect, type Page } from '@playwright/test'
import fs from 'fs'
import path from 'path'
import { apiToken, newWorkflow, N } from './helpers'
// REQ-0080 (TASK-0195): a visitor's file is stored on the configured backend and downloads unchanged with the
// DEC-0072 headers. Run once per backend: E2E_ATTACHMENT_STORAGE=db (default) and E2E_ATTACHMENT_STORAGE=fs.
const shot = async (page: Page, name: string) => { if (process.env.REVIEW_SHOTS) await page.screenshot({ path: `${process.env.REVIEW_SHOTS}/${name}.png` }) }
const BACKEND = process.env.E2E_ATTACHMENT_STORAGE || 'db'
const ROOT = path.resolve('../backend/.e2e-attachments')  // playwright runs from frontend/
const STATE = [{ name: 'message', type: 'string' }, { name: 'files', type: 'list' }, { name: 'reply', type: 'string' }]
const BOT = (name: string) => ({ name, state: STATE,
  nodes: [N('s', 'start', 40), N('bot', 'llm', 300, { label: 'Bot', model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'reply', include_attachments: true }), N('e', 'end', 560)],
  edges: [{ id: '1', source: 's', target: 'bot' }, { id: '2', source: 'bot', target: 'e' }] })
const BODY = Buffer.from('id,total\n42,99\n'.repeat(2000))
const T = { vi: 'Tệp đính kèm: tài liệu totals.csv', en: 'Attachments: document totals.csv' }

for (const lang of ['vi', 'en'] as const) test.describe(lang, () => {
  test.use({ locale: lang === 'vi' ? 'vi-VN' : 'en-US' })

  test(`a file is kept on ${BACKEND} and downloads unchanged (${lang})`, async ({ page, browser }) => {
    await page.goto('/login'); await page.locator('#email').fill('admin@example.com'); await page.locator('#password').fill('admin123')
    await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
    const H = { Authorization: `Bearer ${await apiToken(page)}` }; const n = Date.now() % 100000
    const wid = await newWorkflow(page, H, BOT(`Store ${lang} ${n}`)); const slug = `store-${lang}-${n}`
    const put = await page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true, access: 'anonymous', slug, input_field: 'message',
      reply_field: 'reply', attachments: { enabled: true, kinds: ['document', 'image'], max_files: 5, max_mb: 10, field: 'files' } } })
    expect(put.ok()).toBeTruthy()
    const health = (await (await page.request.get('/api/health')).json()).data
    expect(health.attachment_storage).toBe(BACKEND); expect(health.attachment_storage_ok).toBe(true)

    const ctx = await browser.newContext({ locale: lang === 'vi' ? 'vi-VN' : 'en-US' }); const v = await ctx.newPage()
    await v.goto(`/c/${slug}`)
    const ids: string[] = []
    v.on('response', async r => { if (r.request().method() === 'POST' && r.url().includes('/attachments')) ids.push((await r.json()).data.id) })
    await v.locator('#chat-file-input').setInputFiles({ name: 'totals.csv', mimeType: 'text/csv', buffer: BODY })
    await expect(v.locator('[data-testid="chat-file"][data-state="done"]')).toHaveCount(1)
    await v.locator('#chat-input').fill(lang === 'vi' ? 'Tổng là bao nhiêu?' : 'What is the total?'); await v.keyboard.press('Enter')
    await expect(v.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
    await expect(v.getByTestId('chat-answer').last()).toContainText(T[lang])

    const dl = v.waitForEvent('download'); await v.getByTestId('chat-file-download').first().click()
    const file = await dl; expect(file.suggestedFilename()).toBe('totals.csv')
    expect(fs.readFileSync(await file.path() as string).equals(BODY)).toBeTruthy()
    await shot(v, `r011-storage-${BACKEND}-thread-${lang}`)
    const sid = (await (await v.request.get(`/api/public/chat/${slug}/sessions`)).json()).data.sessions[0].id
    const r = await v.request.get(`/api/public/chat/${slug}/sessions/${sid}/attachments/${ids[0]}`, { headers: { 'X-Requested-With': 'studio' } })
    expect(r.status()).toBe(200)
    expect(r.headers()['content-disposition']).toContain('attachment'); expect(r.headers()['x-content-type-options']).toBe('nosniff')
    expect(r.headers()['cache-control']).toBe('private, no-store')
    const onDisk = path.join(ROOT, wid, sid, ids[0])
    expect(fs.existsSync(onDisk)).toBe(BACKEND === 'fs')   // fs: a file under the folder; db: nothing outside the database
    if (BACKEND === 'fs') expect(fs.readFileSync(onDisk).equals(BODY)).toBeTruthy()
    await ctx.close()
  })
})
