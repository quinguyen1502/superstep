import { readFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'
import { signIn } from './helpers'

test('previews, maps, imports and downloads Dataset CSV', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'))
  await page.goto('/login')
  await signIn(page, 'admin@example.com', 'admin123')
  await page.goto('/datasets')
  await page.getByRole('button', { name: 'Create dataset' }).click()
  await page.getByRole('button', { name: 'Create from CSV' }).click()
  const creator = page.getByRole('dialog', { name: 'Create from CSV' })
  await creator.getByLabel('CSV file').setInputFiles({
    name: 'CSV tickets.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from('\ufeffTicket,Score,Notes\r\nA,0,"hello, world"\r\nB,2,"=formula"\r\n'),
  })
  await expect(creator.getByRole('table', { name: 'CSV preview' })).toContainText('hello, world')
  await expect(creator.getByRole('button', { name: 'Import CSV' })).toBeDisabled()
  await creator.getByRole('button', { name: 'Check rows' }).click()
  await creator.getByRole('button', { name: 'Import CSV' }).click()
  await expect(page.getByRole('heading', { name: 'CSV tickets' })).toBeVisible()
  const rows = page.getByTestId('dataset-row')
  await expect(rows).toHaveCount(2)

  const actions = page.getByRole('button', { name: 'Dataset actions' })
  await actions.click()
  await page.getByRole('menuitem', { name: 'Import CSV' }).click()
  const importer = page.getByRole('dialog', { name: 'Import CSV' })
  await importer.getByLabel('CSV file').setInputFiles({
    name: 'additional.csv', mimeType: 'text/csv', buffer: Buffer.from('Ref,Score,Notes\nC,invalid,Corrected mapping\n'),
  })
  await expect(importer.getByRole('alert')).toContainText('Line 2')
  await expect(importer.getByRole('button', { name: 'Import CSV' })).toBeDisabled()
  await expect(rows).toHaveCount(2)
  await importer.getByRole('combobox', { name: 'Map source column 1 (Ref)' }).click()
  await page.getByRole('option', { name: 'Ticket', exact: true }).click()
  await importer.getByRole('combobox', { name: 'Map source column 2 (Score)' }).click()
  await page.getByRole('option', { name: 'Skip column', exact: true }).click()
  await importer.getByRole('button', { name: 'Check rows' }).click()
  await expect(importer.getByRole('alert')).toHaveCount(0)
  await importer.getByRole('button', { name: 'Import CSV' }).click()
  await expect(rows).toHaveCount(3)
  await expect(rows.last()).toContainText('Corrected mapping')

  await actions.click()
  const download = page.waitForEvent('download')
  await page.getByRole('menuitem', { name: 'Export CSV' }).click()
  const file = await download
  expect(file.suggestedFilename()).toBe('CSV tickets.csv')
  const exported = await readFile(await file.path(), 'utf8')
  expect(exported).toContain('Ticket,Score,Notes')
  expect(exported).toContain("'=formula")
  expect(exported).toContain('C,,Corrected mapping')
})
