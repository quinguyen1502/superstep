import { test, expect } from '@playwright/test'
import { login, newWorkflow, SIMPLE } from './helpers'
import { expectRowAligned, settled } from './helpers/alignment'

test.use({ screenshot: 'off', trace: 'off' })  // a failure while a copy-once secret is open must not capture it

for (const lang of ['en', 'vi'] as const) for (const theme of ['light', 'dark'] as const) {
  test(`app key rotation and typed revocation (${lang}, ${theme})`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 })
    const headers = await login(page)
    const wid = await newWorkflow(page, headers, SIMPLE('App key review'))
    const saved = await page.request.put(`/api/workflows/${wid}/chat`, { headers, data: {
      enabled: true, access: ['anonymous', 'app'], slug: `keys-${lang}-${theme}-${Date.now()}`,
    } })
    expect(saved.ok()).toBe(true)
    await page.evaluate(([l, t]) => { localStorage.setItem('lang', l); localStorage.setItem('theme', t) }, [lang, theme])
    await page.goto(`/workflows/${wid}`)
    if (await page.locator('#chat-open').getAttribute('aria-pressed') !== 'true') await page.locator('#chat-open').click()
    await page.locator('#chat-view').click()
    await page.locator('#chat-settings-btn').click()
    await expect(page.locator('#chat-access-anonymous')).toBeChecked()
    await expect(page.locator('#chat-access-app')).toBeChecked()
    await page.locator('#chat-key-label').fill('Production')
    await page.locator('#chat-key-origins').fill('https://shop.example.com')
    await page.locator('#chat-key-create').click()
    await expect(page.locator('#chat-key-secret')).toBeVisible()
    // Wait for the nested modal to own focus so Escape dismisses that modal.
    await expect.poll(() => page.evaluate(() => Boolean(document.activeElement?.closest('#chat-key-secret')))).toBe(true)
    const secret = await page.locator('#chat-key-secret-value').inputValue()
    expect(secret.length).toBeGreaterThan(40)
    await page.keyboard.press('Escape')
    await expect(page.locator('#chat-key-secret')).toBeHidden()
    expect(await page.locator('#chat-app-keys').textContent()).not.toContain(secret)
    await page.locator('#chat-key-label').fill('Rotation')
    await page.locator('#chat-key-create').click()
    await expect(page.locator('#chat-key-secret')).toBeVisible()
    await expect.poll(() => page.evaluate(() => Boolean(document.activeElement?.closest('#chat-key-secret')))).toBe(true)
    await page.keyboard.press('Escape')
    await expect(page.locator('#chat-key-secret')).toBeHidden()
    await expect(page.getByTestId('chat-app-key')).toHaveCount(2)
    await expect(page.locator('#chat-key-create')).toBeDisabled()
    await settled(page.locator('#chat-settings'))
    await expect(page.locator('#chat-settings')).toBeVisible()
    await page.locator('#chat-app-keys').scrollIntoViewIfNeeded()
    await expectRowAligned(await page.getByTestId('chat-app-key').first().locator('> div > *').all(), { sameHeight: false, label: 'app key actions' })
    // Only the list is captured: copy-once secrets are never screenshots or logs.
    if (process.env.REVIEW_SHOTS) await page.locator('#chat-app-keys').screenshot({ path: `${process.env.REVIEW_SHOTS}/app-keys-${lang}-${theme}.png` })
    await page.getByTestId('chat-app-key').first().getByRole('button').click()
    await expect(page.locator('#confirm-delete-submit')).toBeDisabled()
    await page.locator('#confirm-delete-input').fill('production')
    await expect(page.locator('#confirm-delete-submit')).toBeDisabled()
    await page.locator('#confirm-delete-input').fill('Production')
    await page.locator('#confirm-delete-submit').click()
    await expect(page.locator('#confirm-delete')).toBeHidden()
    await page.locator('#chat-key-label').fill('Replacement')
    await expect(page.locator('#chat-key-create')).toBeEnabled()
    // Close and reopen: the secret is gone, while revocation and access modes persist.
    await page.keyboard.press('Escape')
    await page.locator('#chat-view').click()
    await page.locator('#chat-settings-btn').click()
    await expect(page.getByTestId('chat-app-key')).toHaveCount(2)
    await expect(page.locator('#chat-key-secret')).toBeHidden()
    await expect(page.locator('#chat-access-app')).toBeChecked()
  })
}
