import { test, expect, type Page } from '@playwright/test'
import { apiToken, newWorkflow, N } from './helpers'
// REQ-0077 (TASK-0178): a visitor attaches a PDF and an image on the published chat page. A file over the limit is
// refused in the page before upload. The mock answer names both files, the sent message lists them with downloads,
// and another visitor cannot download them. The builder sets the limits in Chat settings and reads the files under Visitors.
const shot = async (page: Page, name: string, sel = 'body') => { if (process.env.REVIEW_SHOTS) await page.locator(sel).screenshot({ path: `${process.env.REVIEW_SHOTS}/${name}.png` }) }
const STATE = [{ name: 'message', type: 'string' }, { name: 'files', type: 'list' }, { name: 'reply', type: 'string' }]
const BOT = (name: string) => ({ name, state: STATE,
  nodes: [N('s', 'start', 40), N('bot', 'llm', 300, { label: 'Bot', model: 'gpt-4o-mini', prompt: '{{state.message}}', output_field: 'reply', include_attachments: true }), N('e', 'end', 560)],
  edges: [{ id: '1', source: 's', target: 'bot' }, { id: '2', source: 'bot', target: 'e' }] })
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64')
/** A one-page PDF with a text layer (as backend/tests/chat_files.py). */
function pdf(text = 'Invoice 42 total 99 USD') {
  const stream = `BT /F1 12 Tf 20 100 Td (${text}) Tj ET`
  const objs = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`, '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
  let out = '%PDF-1.4\n'; const offsets: number[] = []
  objs.forEach((o, i) => { offsets.push(out.length); out += `${i + 1} 0 obj\n${o}\nendobj\n` })
  const xref = out.length
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n` + offsets.map(o => `${String(o).padStart(10, '0')} 00000 n \n`).join('')
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`
  return Buffer.from(out, 'latin1')
}
const T = {
  vi: { answer: 'Tệp đính kèm: tài liệu invoice.pdf, ảnh photo.png', large: 'tối đa 10 MB', off: 'Cho phép đính kèm tệp' },
  en: { answer: 'Attachments: document invoice.pdf, image photo.png', large: '10 MB', off: 'Allow attachments' },
}

for (const lang of ['vi', 'en'] as const) test.describe(lang, () => {
  test.use({ locale: lang === 'vi' ? 'vi-VN' : 'en-US' })

  test(`a visitor attaches a PDF and an image (${lang})`, async ({ page, browser }) => {
    await page.goto('/login'); await page.locator('#email').fill('admin@example.com'); await page.locator('#password').fill('admin123')
    await page.locator('#auth-submit').click(); await expect(page).toHaveURL(/\/workflows$/)
    const H = { Authorization: `Bearer ${await apiToken(page)}` }; const n = Date.now() % 100000
    const wid = await newWorkflow(page, H, BOT(`Files ${lang} ${n}`)); const slug = `files-${lang}-${n}`
    const put = await page.request.put(`/api/workflows/${wid}/chat`, { headers: H, data: { enabled: true, access: 'anonymous', slug, input_field: 'message', reply_field: 'reply' } })
    expect(put.ok()).toBeTruthy()

    // the builder turns attachments on in Chat settings: kinds, limits within the server ceiling, the field
    await page.goto(`/workflows/${wid}`)
    if (await page.locator('#chat-open').getAttribute('aria-pressed') !== 'true') await page.locator('#chat-open').click()
    await expect(page.locator('#chat-view')).toBeVisible()
    if (!await page.locator('#chat-settings-btn').isVisible()) await page.locator('#chat-view').click()   // compact: in the view menu
    await page.locator('#chat-settings-btn').click()
    await expect(page.locator('#chat-attachments')).toContainText(T[lang].off)
    await page.locator('#chat-attachments-enabled').click()
    await expect(page.locator('#chat-attachments-kind-image')).toHaveAttribute('aria-checked', 'true')
    await page.locator('#chat-attachments').scrollIntoViewIfNeeded(); await shot(page, `r010-attachment-settings-${lang}`, '#chat-settings')
    await page.locator('[id="chat-attachments.max_mb"]').fill('99')
    await page.locator('#chat-settings-save').click()
    await expect(page.locator('[id="chat-attachments.max_mb"]')).toHaveAttribute('aria-invalid', 'true')   // over the ceiling
    await page.locator('[id="chat-attachments.max_mb"]').fill('10')
    await page.locator('#chat-settings-save').click(); await expect(page.locator('#chat-settings')).toHaveCount(0)
    // the LLM node shows "Include attachments" on
    await page.locator('.react-flow__node').filter({ hasText: 'Bot' }).click()
    await expect(page.locator('#llm-include-attachments')).toHaveAttribute('aria-checked', 'true')

    // a visitor: a file over the limit is refused before upload; a PDF and an image upload as chips
    const ctx = await browser.newContext({ locale: lang === 'vi' ? 'vi-VN' : 'en-US' }); const v = await ctx.newPage()
    await v.goto(`/c/${slug}`)
    let uploads = 0; v.on('request', r => { if (r.method() === 'POST' && r.url().includes('/attachments')) uploads++ })
    await v.locator('#chat-file-input').setInputFiles({ name: 'big.pdf', mimeType: 'application/pdf', buffer: Buffer.alloc(30 * 1024 * 1024, 32) })
    await expect(v.locator('#public-chat-error')).toContainText(T[lang].large); expect(uploads).toBe(0)
    const ids: string[] = []
    v.on('response', async r => { if (r.request().method() === 'POST' && r.url().includes('/attachments')) ids.push((await r.json()).data.id) })
    await v.locator('#chat-file-input').setInputFiles([{ name: 'invoice.pdf', mimeType: 'application/pdf', buffer: pdf() }, { name: 'photo.png', mimeType: 'image/png', buffer: PNG }])
    await expect(v.locator('#public-chat-error')).toHaveCount(0)   // a good file clears the refusal
    await expect(v.getByTestId('chat-file')).toHaveCount(2); await expect(v.locator('[data-testid="chat-file"][data-state="done"]')).toHaveCount(2)
    await expect(v.getByTestId('chat-file').nth(1).locator('img')).toBeVisible()   // the image's thumbnail
    await v.locator('#chat-input').fill(lang === 'vi' ? 'Tổng hoá đơn là bao nhiêu?' : 'What is the invoice total?')
    await shot(v, `r010-attachment-composer-${lang}`, '#chat-form')
    await v.keyboard.press('Enter')
    await expect(v.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok', { timeout: 20_000 })
    await expect(v.getByTestId('chat-answer').last()).toContainText(T[lang].answer)
    await expect(v.getByTestId('chat-turn-file')).toHaveCount(2)
    const dl = v.waitForEvent('download'); await v.getByTestId('chat-file-download').first().click()
    expect((await dl).suggestedFilename()).toBe('invoice.pdf')
    await shot(v, `r010-attachment-thread-${lang}`)
    await v.reload(); await expect(v.getByTestId('chat-turn-file')).toHaveCount(2)

    // another visitor cannot download them
    const sid = new URL(v.url()).searchParams.get('s') ?? (await (await v.request.get(`/api/public/chat/${slug}/sessions`)).json()).data.sessions[0].id
    const other = await browser.newContext(); const o = await other.newPage(); await o.goto(`/c/${slug}`)
    const r = await o.request.get(`/api/public/chat/${slug}/sessions/${sid}/attachments/${ids[0]}`, { headers: { 'X-Requested-With': 'studio' } })
    expect(r.status()).toBe(404)

    // the builder reads the visitor's chat and downloads its file
    await page.reload(); await page.locator('#chat-session-picker').click()
    await page.getByTestId('chat-visitor-option').first().click()
    await expect(page.getByTestId('chat-turn-file')).toHaveCount(2)
    const bdl = page.waitForEvent('download'); await page.getByTestId('chat-file-download').nth(1).click()
    expect((await bdl).suggestedFilename()).toBe('photo.png')
    await ctx.close(); await other.close()
  })
})
