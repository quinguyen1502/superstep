import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, Pencil, Plus, RotateCw, Trash2 } from 'lucide-react'
import { useConfirmDelete } from '@/components/use-confirm-delete'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { api } from '@/lib/api'
import { errorText, type ApiErrorBody } from '@/lib/i18n'
import { fmtCount, fmtShare, fmtUsd } from '@/lib/usage'

type Scope = 'user' | 'team'
type Target = { scope: Scope; id: string; name: string }
type Budget = { id: string; scope: Scope; target_id: string; name: string; amount_usd: number; spent_usd: number; unpriced_rows: number }
type BudgetList = { month: string; time_zone: string; budgets: Budget[]; targets: Target[] }

const PATH = '/api/admin/usage/budgets'

export function UsageBudgetsCard() {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage
  const confirmation = useConfirmDelete('usage-budget-delete')
  const [data, setData] = useState<BudgetList | null>(null)
  const [editing, setEditing] = useState<Budget | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [scope, setScope] = useState<Scope>('user')
  const [target, setTarget] = useState('')
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const reload = useCallback(() => api<BudgetList>(PATH).then(
    next => { setData(next); setError('') },
    e => setError(errorText(e as ApiErrorBody)),
  ), [])
  useEffect(() => { void reload() }, [reload])

  const open = (budget: Budget | null) => {
    setEditing(budget)
    setTarget('')
    setAmount(budget ? String(budget.amount_usd) : '')
    setFormOpen(true)
  }
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (editing) await api(`${PATH}/${editing.id}`, { method: 'PATCH', json: { amount_usd: amount } })
      else await api(PATH, { method: 'POST', json: { scope, target_id: target, amount_usd: amount } })
      setFormOpen(false)
      await reload()
    } catch (e) { setError(errorText(e as ApiErrorBody)) }
    finally { setBusy(false) }
  }
  const remove = (budget: Budget) => confirmation.ask({
    name: budget.name, title: t('settings.usage.budgets.deleteTitle', { name: budget.name }),
    description: t('settings.usage.budgets.deleteBody'),
    onConfirm: async () => {
      await api(`${PATH}/${budget.id}`, { method: 'DELETE' })
      if (editing?.id === budget.id) setFormOpen(false)
      await reload()
    },
  })
  const options = data?.targets.filter(item => item.scope === scope &&
    !data.budgets.some(budget => budget.scope === scope && budget.target_id === item.id)) ?? []

  return <Card id="usage-budgets">
    <CardHeader>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <CardTitle>{t('settings.usage.budgets.title')}</CardTitle>
        {data && !formOpen && <Button size="sm" onClick={() => open(null)}><Plus />{t('settings.usage.budgets.add')}</Button>}
      </div>
      <CardDescription>{data
        ? t('settings.usage.budgets.period', { month: data.month, zone: data.time_zone })
        : t('settings.usage.budgets.description')}</CardDescription>
    </CardHeader>
    <CardContent className="space-y-4">
      {error && <Alert variant="destructive"><AlertCircle /><AlertDescription className="flex items-center gap-2">
        <span>{error}</span><Button variant="outline" size="sm" onClick={() => void reload()}><RotateCw />{t('common.retry')}</Button>
      </AlertDescription></Alert>}
      {formOpen && <form className="grid items-end gap-3 sm:grid-cols-2" onSubmit={save}>
        {editing ? <p className="text-sm font-medium sm:col-span-2">{editing.name}</p> : <>
          <div className="space-y-1.5">
            <Label htmlFor="usage-budget-scope">{t('settings.usage.budgets.scope')}</Label>
            <Select value={scope} onValueChange={value => { setScope(value as Scope); setTarget('') }}>
              <SelectTrigger id="usage-budget-scope" className="w-full"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="user">{t('settings.usage.budgets.user')}</SelectItem>
                <SelectItem value="team">{t('settings.usage.budgets.team')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="usage-budget-target">{t('settings.usage.budgets.target')}</Label>
            <Select value={target} onValueChange={setTarget} disabled={!options.length}>
              <SelectTrigger id="usage-budget-target" className="w-full"><SelectValue placeholder={t(options.length
                ? 'settings.usage.budgets.chooseTarget' : 'settings.usage.budgets.noTargets')} /></SelectTrigger>
              <SelectContent>{options.map(item => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </>}
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="usage-budget-amount">{t('settings.usage.budgets.amount')}</Label>
          <div className="flex items-center gap-2">
            <Input id="usage-budget-amount" className="min-w-0 flex-1" type="number" min="0.01" max="9999999.99" step="0.01" required
              value={amount} onChange={event => setAmount(event.target.value)} />
            <Button type="submit" disabled={busy || (!editing && !target)}>{t('common.save')}</Button>
            <Button type="button" variant="outline" disabled={busy} onClick={() => setFormOpen(false)}>{t('common.cancel')}</Button>
          </div>
        </div>
      </form>}
      {data?.budgets.length ? <Table>
        <TableHeader><TableRow>
          <TableHead>{t('settings.usage.budgets.target')}</TableHead>
          <TableHead className="text-right">{t('settings.usage.budgets.amount')}</TableHead>
          <TableHead className="text-right">{t('settings.usage.budgets.spent')}</TableHead>
          <TableHead className="text-right">{t('settings.usage.budgets.used')}</TableHead>
          <TableHead><span className="sr-only">{t('settings.usage.budgets.actions')}</span></TableHead>
        </TableRow></TableHeader>
        <TableBody>{data.budgets.map(budget => <TableRow key={budget.id}>
          <TableCell>{budget.name}<div className="text-xs text-muted-foreground">{t(`settings.usage.budgets.${budget.scope}`)}</div></TableCell>
          <TableCell className="text-right tabular-nums">{fmtUsd(budget.amount_usd, lang)}</TableCell>
          <TableCell className="text-right tabular-nums">{budget.unpriced_rows
            ? t('settings.usage.atLeast', { value: fmtUsd(budget.spent_usd, lang) }) : fmtUsd(budget.spent_usd, lang)}
            {budget.unpriced_rows > 0 && <div className="text-xs text-muted-foreground">
              {t('settings.usage.budgets.unpriced', { count: fmtCount(budget.unpriced_rows, lang) })}
            </div>}
          </TableCell>
          <TableCell className="text-right tabular-nums">{fmtShare(budget.spent_usd / budget.amount_usd, lang)}</TableCell>
          <TableCell className="text-right">
            <Button variant="ghost" size="icon" aria-label={t('settings.usage.budgets.editLabel', { name: budget.name })}
              disabled={busy} onClick={() => open(budget)}><Pencil /></Button>
            <Button variant="ghost" size="icon" aria-label={t('settings.usage.budgets.deleteTitle', { name: budget.name })}
              disabled={busy} onClick={() => remove(budget)}><Trash2 /></Button>
          </TableCell>
        </TableRow>)}</TableBody>
      </Table> : data
        ? <p className="text-sm text-muted-foreground">{t('settings.usage.budgets.empty')}</p>
        : !error && <p aria-live="polite" className="text-sm text-muted-foreground">{t('common.loading')}</p>}
      {confirmation.dialog}
    </CardContent>
  </Card>
}
