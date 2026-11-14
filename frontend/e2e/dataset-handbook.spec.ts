// Real Studio captures for the Datasets handbook.
// Run: HANDBOOK_SHOTS=1 npm run e2e -- dataset-handbook
import { expect, test, type Page } from '@playwright/test'
import { vt, vin } from './catalog'
import { signIn } from './helpers'

test.skip(!process.env.HANDBOOK_SHOTS, 'set HANDBOOK_SHOTS=1 to capture handbook screenshots')
test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 })
test.setTimeout(120_000)

const COPY = {
  en: {
    actions: 'Dataset actions', importCsv: 'Import CSV', file: 'CSV file', preview: 'CSV preview',
    name: 'Support tickets', subject: 'Printer jam',
  },
  vi: {
    actions: vt('dataset.datasetActions'), importCsv: vt('dataset.importCsv'), file: vt('dataset.csvFile'), preview: vt('dataset.csvPreview'),
    name: vin('handbook.names.dataset'), subject: vin('handbook.names.printer'),
  },
} as const

async function shot(page: Page, lang: 'en' | 'vi', name: string) {
  await page.mouse.move(2, 898)
  await page.waitForTimeout(400)
  await page.screenshot({ path: `../handbook/docs/${lang}/images/${name}.png` })
}

test('capture the dataset grid, a narrow layout, and the CSV preview', async ({ browser }) => {
  for (const lang of ['en', 'vi'] as const) {
    const copy = COPY[lang]
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5, locale: lang === 'vi' ? 'vi-VN' : 'en-US',
    })
    const page = await context.newPage()
    await page.addInitScript(value => { localStorage.setItem('lang', value); localStorage.setItem('theme', 'light') }, lang)
    await page.goto('/login')
    const token = await signIn(page, 'admin@example.com', 'admin123')
    const headers = { Authorization: `Bearer ${token}` }
    const existing = await page.request.get('/api/datasets', { headers })
    expect(existing.ok()).toBeTruthy()
    for (const item of (await existing.json()).data.items as { id: string }[]) {
      const detail = await page.request.get(`/api/datasets/${item.id}`, { headers })
      const revision = (await detail.json()).data.revision
      expect((await page.request.delete(`/api/datasets/${item.id}?revision=${revision}`, { headers })).ok()).toBeTruthy()
    }
    const created = await page.request.post('/api/datasets', {
      headers, data: {
        name: copy.name,
        columns: [
          { key: 'ticket', label: 'Ticket', kind: 'text', required: true, unique: true },
          { key: 'subject', label: 'Subject', kind: 'text' },
          { key: 'score', label: 'Score', kind: 'number' },
        ],
      },
    })
    expect(created.ok(), await created.text()).toBeTruthy()
    const dataset = (await created.json()).data
    for (const [ticket, subject, score] of [['A', copy.subject, 0], ['B', 'New laptop', 1], ['C', 'VPN access', 2]] as const) {
      const row = await page.request.post(`/api/datasets/${dataset.id}/rows`, { headers, data: { values: { ticket, subject, score } } })
      expect(row.ok(), await row.text()).toBeTruthy()
    }
    await page.goto(`/datasets/${dataset.id}`)
    await expect(page.getByRole('heading', { name: copy.name })).toBeVisible()
    await expect(page.getByTestId('dataset-row')).toHaveCount(3)
    await shot(page, lang, 'datasets-grid')
    await page.evaluate(() => {
      localStorage.setItem('theme', 'dark')
      document.documentElement.classList.add('dark')
    })
    await shot(page, lang, 'datasets-grid-dark')
    await page.evaluate(() => {
      localStorage.setItem('theme', 'light')
      document.documentElement.classList.remove('dark')
    })

    await page.setViewportSize({ width: 390, height: 844 })
    await expect(page.getByTestId('dataset-row').first()).toBeVisible()
    await shot(page, lang, 'datasets-narrow')
    await page.setViewportSize({ width: 1440, height: 900 })

    await page.getByRole('button', { name: copy.actions }).click()
    await page.getByRole('menuitem', { name: copy.importCsv }).click()
    const dialog = page.getByRole('dialog', { name: copy.importCsv })
    await dialog.getByLabel(copy.file).setInputFiles({
      name: 'tickets.csv', mimeType: 'text/csv',
      buffer: Buffer.from('Ticket,Subject,Score\nD,Badge printer,0\n'),
    })
    await expect(dialog.getByRole('table', { name: copy.preview })).toContainText('Badge printer')
    await shot(page, lang, 'datasets-csv')
    await context.close()
  }
})
