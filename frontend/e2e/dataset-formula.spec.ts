import path from 'node:path'
import { expect, test, type Page } from '@playwright/test'
import { signIn } from './helpers'

async function dataset(page: Page, name: string, withRows: boolean) {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'))
  await page.goto('/login')
  const headers = { Authorization: 'Bearer ' + await signIn(page, 'admin@example.com', 'admin123') }
  const response = await page.request.post('/api/datasets', { headers, data: { name, columns: [
    { key: 'ticket', label: 'Ticket ID', kind: 'auto_number' },
    { key: 'subject', label: 'Subject', kind: 'text' },
    { key: 'hours', label: 'Hours', kind: 'number' },
    { key: 'rate', label: 'Hourly rate', kind: 'number' },
  ] } })
  expect(response.ok(), await response.text()).toBeTruthy()
  const { id } = (await response.json()).data
  if (withRows) {
    for (const values of [
      { subject: 'Printer jam', hours: 4, rate: 37.5 },
      { subject: 'Network upgrade', hours: 0, rate: 50 },
      { subject: 'Invoice copy', hours: 2, rate: 45 },
    ]) {
      const row = await page.request.post('/api/datasets/' + id + '/rows', { headers, data: { values } })
      expect(row.ok(), await row.text()).toBeTruthy()
    }
  }
  return id as string
}

async function addFormula(page: Page, id: string) {
  await page.goto('/datasets/' + id + '?tab=schema')
  await page.getByRole('button', { name: 'Add column', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Add column' })
  await dialog.getByLabel('Column label').fill('Cost')
  await dialog.getByLabel('Field key').fill('cost')
  await dialog.getByRole('combobox', { name: 'Column type' }).click()
  await page.getByRole('option', { name: 'Formula', exact: true }).click()
  return dialog
}

async function screenshot(page: Page, filename: string) {
  if (!process.env.FORMULA_SHOTS) return
  await page.screenshot({ path: path.join(process.env.FORMULA_SHOTS, filename), animations: 'disabled' })
}

test('previews, saves, and reads a Formula column with real stored rows', async ({ page }) => {
  await page.setViewportSize({ width: 1360, height: 760 })
  const id = await dataset(page, 'Support tickets', true)
  const dialog = await addFormula(page, id)
  const expression = dialog.getByRole('textbox', { name: 'Formula expression' })
  await dialog.getByRole('button', { name: 'Insert field' }).click()
  await page.getByRole('menuitem', { name: 'Hours hours' }).click()
  await expect(expression).toHaveValue('[hours]')
  await expression.fill('[hours] +')
  await expect(dialog.getByRole('alert')).toHaveCount(0)
  await expression.press('Tab')
  await expect(dialog.getByRole('alert')).toContainText('Check the formula syntax. At character')
  await expression.fill('[hours] * [rate]')
  await dialog.getByRole('button', { name: 'Preview', exact: true }).click()
  await expect(dialog.getByRole('status')).toHaveText('150')
  await screenshot(page, 'formula-studio-schema.png')
  await dialog.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByRole('table', { name: 'Schema' }).getByRole('cell', { name: 'Formula', exact: true })).toBeVisible()

  await page.getByRole('tab', { name: 'Rows' }).click()
  const printer = page.getByTestId('dataset-row').filter({ hasText: 'Printer jam' })
  const cost = printer.getByRole('button', { name: 'Cost: 150', exact: true })
  await expect(cost).toBeVisible()
  await cost.dblclick()
  await expect(printer.getByRole('spinbutton', { name: 'Cost' })).toHaveCount(0)
  await printer.getByRole('button', { name: 'Edit Hours: 4' }).dblclick()
  const hours = printer.getByRole('spinbutton', { name: 'Hours' })
  await hours.fill('6')
  await hours.press('Enter')
  await expect(printer.getByRole('button', { name: 'Cost: 225', exact: true })).toBeVisible()
  await screenshot(page, 'formula-studio-rows.png')

  await page.getByRole('tab', { name: 'Schema' }).click()
  await page.getByRole('button', { name: 'Edit Cost', exact: true }).click()
  const edit = page.getByRole('dialog', { name: 'Edit column' })
  await expect(edit.getByRole('combobox', { name: 'Result type' })).toBeDisabled()
  await edit.getByRole('textbox', { name: 'Formula expression' }).fill('[rate] / [hours]')
  await edit.getByRole('button', { name: 'Save', exact: true }).click()
  await expect(edit).toBeHidden()
  await page.getByRole('tab', { name: 'Rows' }).click()
  const network = page.getByTestId('dataset-row').filter({ hasText: 'Network upgrade' })
  await expect(network.getByRole('button', { name: 'Cost: Division by zero.', exact: true })).toBeVisible()
  await screenshot(page, 'formula-studio-error.png')
})

test('previews empty-table sample inputs on a narrow screen in dark mode', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.addInitScript(() => localStorage.setItem('theme', 'dark'))
  const id = await dataset(page, 'Empty tickets', false)
  const dialog = await addFormula(page, id)
  await dialog.getByRole('textbox', { name: 'Formula expression' }).fill('[rate] / [hours]')
  await dialog.getByRole('button', { name: 'Preview', exact: true }).click()
  await expect(dialog.getByRole('status')).toHaveText('No value for these inputs.')
  await dialog.getByRole('spinbutton', { name: 'Hours' }).fill('0')
  await dialog.getByRole('spinbutton', { name: 'Hourly rate' }).fill('60')
  await dialog.getByRole('button', { name: 'Preview', exact: true }).click()
  await expect(dialog.getByRole('status')).toHaveText('Division by zero.')
  await dialog.getByRole('spinbutton', { name: 'Hours' }).fill('3')
  await dialog.getByRole('button', { name: 'Preview', exact: true }).click()
  await expect(dialog.getByRole('status')).toHaveText('20')
  await screenshot(page, 'formula-studio-mobile-dark.png')
  const dimensions = await dialog.evaluate(element => {
    const { left, right } = element.getBoundingClientRect()
    return { left, right, viewport: innerWidth }
  })
  expect(dimensions.left).toBeGreaterThanOrEqual(0)
  expect(dimensions.right).toBeLessThanOrEqual(dimensions.viewport)
})
