import { test, expect } from '@playwright/test'
import { signIn, newWorkflow, N } from './helpers'
test.use({ trace: 'off' })

for (const locale of ['vi', 'en'] as const) test.describe(locale, () => {
  test.use({ locale: locale === 'vi' ? 'vi-VN' : 'en-US' })
  const text = locale === 'vi'
    ? { edit: 'Sửa tin nhắn', save: 'Lưu và chạy trong nhánh mới', cancel: 'Huỷ', source: 'Cuộc trò chuyện gốc', regenerate: 'Tạo lại câu trả lời', run: 'Chạy lại trong nhánh mới' }
    : { edit: 'Edit message', save: 'Save and run in new branch', cancel: 'Cancel', source: 'Original conversation', regenerate: 'Regenerate answer', run: 'Run again in new branch' }

  test('Studio and cookie-backed public chat keep originals when editing', async ({ page, browser }, info) => {
    await page.goto('/login'); const token = await signIn(page, 'admin@example.com', 'admin123')
    const headers = { Authorization: `Bearer ${token}` }
    const slug = `edit-${locale}-${Date.now()}`
    const wid = await newWorkflow(page, headers, { name: slug,
      state: [{ name: 'message', type: 'string' }, { name: 'messages', type: 'list' }, { name: 'reply', type: 'string' }],
      nodes: [N('s', 'start', 40), N('bot', 'llm', 300, { prompt: 'History {{state.messages}}', output_field: 'reply' }), N('e', 'end', 560)],
      edges: [{ id: '1', source: 's', target: 'bot' }, { id: '2', source: 'bot', target: 'e' }] })
    expect((await (await page.request.put(`/api/workflows/${wid}/chat`, { headers, data: { enabled: true, access: 'anonymous', slug } })).json()).success).toBe(true)
    await page.goto(`/workflows/${wid}`)
    if (await page.locator('#chat-open').getAttribute('aria-pressed') !== 'true') await page.locator('#chat-open').click()
    const studio = page.locator('#chat-panel')
    await studio.locator('#chat-input').fill('Studio original'); await studio.locator('#chat-input').press('Enter')
    await expect(studio.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok')
    await studio.getByRole('button', { name: text.edit, exact: true }).click()
    const dialog = page.getByRole('alertdialog')
    await dialog.getByRole('textbox').fill('Studio edited')
    await dialog.getByRole('button', { name: text.cancel, exact: true }).click()
    await expect(studio.getByTestId('chat-mine').first()).toHaveText('Studio original')
    await studio.getByRole('button', { name: text.edit, exact: true }).click()
    await dialog.getByRole('textbox').fill('Studio edited')
    const shot = info.outputPath(`edit-studio-${locale}.png`)
    await page.screenshot({ path: shot, fullPage: true, animations: 'disabled' }); await info.attach(`edit-studio-${locale}`, { path: shot, contentType: 'image/png' })
    await dialog.getByRole('button', { name: text.save }).click()
    await expect(studio.getByTestId('chat-mine').first()).toHaveText('Studio edited')
    await expect(studio.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok')
    await studio.getByRole('button', { name: text.source }).click()
    await expect(studio.getByTestId('chat-mine').first()).toHaveText('Studio original')
    await studio.getByRole('button', { name: text.regenerate, exact: true }).click()
    await dialog.getByRole('button', { name: text.cancel, exact: true }).click()
    await expect(studio.getByRole('button', { name: text.source })).toHaveCount(0)
    await studio.getByRole('button', { name: text.regenerate, exact: true }).click()
    const regenShot = info.outputPath(`regenerate-studio-${locale}.png`)
    await page.screenshot({ path: regenShot, fullPage: true, animations: 'disabled' }); await info.attach(`regenerate-studio-${locale}`, { path: regenShot, contentType: 'image/png' })
    await dialog.getByRole('button', { name: text.run }).click()
    await expect(studio.getByRole('button', { name: text.source })).toBeVisible()
    await expect(studio.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok')
    await expect(studio.getByTestId('chat-mine').first()).toHaveText('Studio original')
    await studio.getByRole('button', { name: text.source }).click()

    const context = await browser.newContext({ locale: locale === 'vi' ? 'vi-VN' : 'en-US', colorScheme: locale === 'vi' ? 'light' : 'dark' })
    try {
      const visitor = await context.newPage(); await visitor.goto(`/c/${slug}`)
      await visitor.locator('#chat-input').fill('Public original'); await visitor.locator('#chat-input').press('Enter')
      await expect(visitor.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok')
      await visitor.getByRole('button', { name: text.edit, exact: true }).click()
      await visitor.getByRole('alertdialog').getByRole('textbox').fill('Public edited')
      await visitor.getByRole('button', { name: text.save }).click()
      await expect(visitor.getByTestId('chat-mine').first()).toHaveText('Public edited')
      await expect(visitor.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok')
      await visitor.reload(); await expect(visitor.getByTestId('chat-mine').first()).toHaveText('Public edited')
      await visitor.getByRole('button', { name: text.source }).click()
      await expect(visitor.getByTestId('chat-mine').first()).toHaveText('Public original')
      await visitor.getByRole('button', { name: text.regenerate, exact: true }).click()
      const publicShot = info.outputPath(`regenerate-public-${locale}.png`)
      await visitor.screenshot({ path: publicShot, fullPage: true, animations: 'disabled' }); await info.attach(`regenerate-public-${locale}`, { path: publicShot, contentType: 'image/png' })
      await visitor.getByRole('button', { name: text.run }).click()
      await expect(visitor.getByRole('button', { name: text.source })).toBeVisible()
      await expect(visitor.getByTestId('chat-answer').last()).toHaveAttribute('data-status', 'ok')
      await visitor.reload(); await expect(visitor.getByRole('button', { name: text.source })).toBeVisible()
      await visitor.getByRole('button', { name: text.source }).click()
      await expect(visitor.getByTestId('chat-mine').first()).toHaveText('Public original')
    } finally { await context.close() }
  })
})
