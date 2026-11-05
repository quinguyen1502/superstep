import { useContext, useId, useState } from 'react'
import { Plus } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { StudioContext } from '@/components/editor/studio-context'
import type { Field } from '@/components/editor/meta'

const TYPES = ['string', 'number', 'integer', 'boolean', 'object', 'list']

export function StateFieldPicker({ value, onChange, options, types = TYPES, id, noneLabel, disabled }: {
  value?: string; onChange: (name: string) => void; options: string[]; types?: string[]; id?: string; noneLabel?: string; disabled?: boolean
}) {
  const { t } = useTranslation()
  // This reserved UI value is never written to the graph.
  let none = '__no_state_field__'
  while (options.includes(none)) none += '_'
  return <div className="flex min-w-0 items-center gap-2">
    <Select value={value || (noneLabel ? none : '')} onValueChange={v => onChange(v === none ? '' : v)} disabled={disabled}>
      <SelectTrigger id={id} className="min-w-0 flex-1"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
      <SelectContent>{noneLabel && <SelectItem value={none}>{noneLabel}</SelectItem>}
        {options.filter(Boolean).map(name => <SelectItem key={name} value={name}>{name}</SelectItem>)}</SelectContent>
    </Select>
    {!disabled && <StateFieldAction types={types} onCreated={onChange} />}
  </div>
}

/** Explicit, undoable schema creation. Outside the editable Studio graph there is no mutation capability. */
export function StateFieldAction({ types = TYPES, onCreated, compact = true, size = 'icon', className }: {
  types?: string[]; onCreated?: (name: string, field: Field) => void; compact?: boolean; size?: 'icon' | 'icon-xs'; className?: string
}) {
  const studio = useContext(StudioContext); const { t } = useTranslation(); const id = useId()
  const [open, setOpen] = useState(false); const [name, setName] = useState(''); const [type, setType] = useState(types[0] || 'string')
  if (!studio?.editable || !types.length) return null
  const value = name.trim()
  const error = !value ? '' : !/^[A-Za-z_][A-Za-z0-9_]*$/.test(value) ? t('editor.newField.invalid')
    : studio.state.some(f => f.name === value) ? t('editor.newField.duplicate') : ''
  const add = () => {
    if (!value || error || !types.includes(type)) return
    const field: Field = { name: value, type }
    studio.setState(fields => [...fields, field]); onCreated?.(value, field); setOpen(false)
  }
  return <>
    <Button type="button" variant="outline" size={compact ? size : 'default'} className={className || (compact ? undefined : 'w-full')}
      aria-label={t(compact ? 'editor.newField.title' : 'editor.addField')} title={t('editor.newField.title')} onClick={() => { setName(''); setType(types[0]); setOpen(true) }}>
      <Plus />{!compact && t('editor.addField')}
    </Button>
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="flex max-h-[85dvh] flex-col overflow-hidden">
        <DialogHeader><DialogTitle>{t('editor.newField.title')}</DialogTitle><DialogDescription>{t('editor.newField.hint')}</DialogDescription></DialogHeader>
        <DialogBody className="space-y-3">
          <div className="space-y-1.5"><Label htmlFor={`${id}-name`}>{t('editor.fieldName')}</Label>
            <Input id={`${id}-name`} value={name} autoComplete="off" onChange={e => setName(e.target.value)} aria-invalid={!!error}
              aria-describedby={error ? `${id}-error` : undefined} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }} />
            {error && <p id={`${id}-error`} role="alert" className="text-xs text-destructive">{error}</p>}</div>
          <div className="space-y-1.5"><Label htmlFor={`${id}-type`}>{t('editor.fieldType')}</Label>
            <Select value={type} onValueChange={setType}><SelectTrigger id={`${id}-type`} className="w-full"><SelectValue /></SelectTrigger>
              <SelectContent>{types.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}</SelectContent></Select></div>
        </DialogBody>
        <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
          <Button disabled={!value || !!error} onClick={add}><Plus />{t('editor.addField')}</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  </>
}
