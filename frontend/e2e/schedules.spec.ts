import { test, expect } from '@playwright/test'
import { confirmDelete } from './confirm'
import { login, newWorkflow, SIMPLE } from './helpers'
// cron schedules in the editor's ⋯ menu: preset, live preview, bad expression, on/off, delete by name.
// The scheduler firing a run is covered by backend/tests/test_schedules.py with the real worker.
test('schedules: add from a preset, preview, refuse a bad expression, turn off, delete', async ({ page }) => {
  const H = await login(page); const wid = await newWorkflow(page, H, SIMPLE(`Sched ${Date.now()}`))
  await page.goto(`/workflows/${wid}`)
  await page.locator('#more-btn').click(); await page.locator('#schedules-btn').click()
  const dlg = page.locator('#schedules-dialog'); await expect(dlg).toBeVisible()
  await expect(dlg.getByText('Chưa có lịch chạy nào.')).toBeVisible()

  await page.locator('#schedule-tz').click()
  await page.getByRole('option', { name: 'Asia/Saigon', exact: true }).click()
  await page.locator('#schedule-preset').click(); await page.getByRole('option', { name: 'Mỗi giờ' }).click()
  await expect(page.locator('#schedule-cron')).toHaveValue('0 * * * *')
  await expect(page.locator('#schedule-preview')).toContainText('Lần tới:')

  await page.locator('#schedule-cron').fill('61 * * * *')
  await expect(page.locator('#schedule-preview')).toContainText('minute: values must be 0-59'); await expect(page.locator('#schedule-create')).toBeDisabled()
  await page.locator('#schedule-cron').fill('30 9 * * 1-5'); await expect(page.locator('#schedule-create')).toBeEnabled()
  await page.locator('#schedule-name').fill('Morning report'); await page.locator('#schedule-create').click()

  const row = dlg.locator('[data-testid=schedule-row][data-name="Morning report"]')
  await expect(row).toContainText('30 9 * * 1-5'); await expect(row.getByTestId('schedule-next')).toContainText('Asia/Saigon')
  const saved = (await (await page.request.get(`/api/workflows/${wid}/schedules`, { headers: H })).json()).data
  expect(saved).toHaveLength(1); expect(saved[0]).toMatchObject({ name: 'Morning report', cron: '30 9 * * 1-5', timezone: 'Asia/Saigon', enabled: true })

  await row.getByRole('switch').click(); await expect(row.getByTestId('schedule-next')).toHaveText('Tắt')
  await row.getByRole('button', { name: 'Xoá lịch Morning report' }).click(); await confirmDelete(page, 'Morning report')
  await expect(dlg.getByText('Chưa có lịch chạy nào.')).toBeVisible()
})
