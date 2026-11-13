import { expect, test } from '@playwright/test'
import { newWorkflow, signIn, SIMPLE } from './helpers'

test('manages workflow grants and scoped Dataset API tokens', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'))
  await page.goto('/login')
  const headers = { Authorization: `Bearer ${await signIn(page, 'admin@example.com', 'admin123')}` }
  const workflowName = `CSV support ${Date.now()}`
  await newWorkflow(page, headers, SIMPLE(workflowName))
  const result = await page.request.post('/api/datasets', { headers, data: { name: 'Accessible dataset' } })
  expect(result.ok()).toBeTruthy()
  const dataset = (await result.json()).data
  await page.goto(`/datasets/${dataset.id}`)
  await page.getByRole('button', { name: 'Dataset actions' }).click()
  await page.getByRole('menuitem', { name: 'Access', exact: true }).click()
  const access = page.getByRole('dialog', { name: 'Access' })
  await access.getByRole('combobox', { name: 'Workflow', exact: true }).click()
  await page.getByRole('option', { name: workflowName, exact: true }).click()
  await access.getByRole('button', { name: 'Save grant' }).click()
  await expect(access.getByRole('paragraph').filter({ hasText: workflowName })).toBeVisible()
  await access.getByRole('button', { name: 'Revoke access', exact: true }).click()
  const confirm = page.getByRole('alertdialog')
  const submit = confirm.locator('[id$="-submit"]')
  await expect(submit).toBeDisabled()
  await confirm.getByRole('textbox').fill(workflowName)
  await submit.click()
  await expect(access.getByText('No workflow grants.')).toBeVisible()

  await access.getByLabel('Token name').fill('Deployment')
  await access.getByRole('button', { name: 'Create token' }).click()
  const secret = access.getByLabel('New token')
  await expect(secret).toHaveValue(/^dsat_/)
  const first = await secret.inputValue()
  await access.getByRole('button', { name: 'Rotate token' }).click()
  await expect(secret).not.toHaveValue(first)
  await expect(secret).toHaveValue(/^dsat_/)
  await access.getByRole('button', { name: 'Revoke access', exact: true }).click()
  await expect(submit).toBeDisabled()
  await confirm.getByRole('textbox').fill('Deployment')
  await submit.click()
  await expect(access.getByText('No API tokens.')).toBeVisible()
  await expect(secret).toHaveCount(0)
})
