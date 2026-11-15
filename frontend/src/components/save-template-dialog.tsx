/** Editor "Save as template": copies the saved workflow, minus credentials / resource refs / secrets (server-side sanitiser). */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, CheckCircle2, LayoutTemplate, Loader2, TriangleAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useOpenState } from '@/lib/use-open-state'
import { api } from '@/lib/api'
import { can, useMe } from '@/lib/rbac'
import { useLoadWhen } from '@/lib/use-when'

export function SaveTemplateDialog(props: { wid?: string | null; defaultName: string; isDirty: () => boolean; open?: boolean; onOpenChange?: (v: boolean) => void }) {
  const { wid, defaultName, isDirty } = props
  const { t } = useTranslation(); const me = useMe()
  const [open, setOpen, controlled] = useOpenState(props.open, props.onOpenChange); const [dirty, setDirty] = useState(false)
  const [name, setName] = useState(''); const [desc, setDesc] = useState(''); const [scope, setScope] = useState<'user' | 'org'>('user')
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [done, setDone] = useState('')
  useLoadWhen(open, () => { setName(defaultName); setDesc(''); setScope('user'); setErr(''); setDone(''); setDirty(isDirty()) })
  const save = async () => {
    if (!wid || !name.trim() || busy) return
    setBusy(true); setErr('')
    try { const r = await api<{ name: string }>('/api/templates', { method: 'POST', json: { workflow_id: wid, name: name.trim(), description: desc.trim() || null, scope } }); setDone(r.name) }
    catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {!controlled && <Tooltip><TooltipTrigger asChild><span className="inline-flex">{/* icon-only keeps the editor toolbar compact */}
        <DialogTrigger asChild><Button size="icon-sm" variant="outline" id="save-template-btn" aria-label={t('templates.saveAs')} disabled={!wid}><LayoutTemplate /></Button></DialogTrigger>
      </span></TooltipTrigger><TooltipContent>{t('templates.saveAs')}</TooltipContent></Tooltip>}
      <DialogContent id="save-template" className="flex max-h-[85dvh] flex-col overflow-hidden">
        <DialogHeader><DialogTitle>{t('templates.saveAsTitle')}</DialogTitle><DialogDescription>{t('templates.saveAsDesc')}</DialogDescription></DialogHeader>
        <DialogBody className="space-y-4">
        {done ? <Alert id="tpl-saved"><CheckCircle2 /><AlertDescription>{t('templates.saved', { name: done })}</AlertDescription></Alert> : <>
          {dirty && <Alert variant="warning" id="tpl-unsaved"><TriangleAlert /><AlertDescription>{t('templates.unsavedNote')}</AlertDescription></Alert>}
          <div className="grid gap-2"><Label htmlFor="tpl-name">{t('templates.name')}</Label>
            <Input id="tpl-name" value={name} maxLength={120} onChange={e => setName(e.target.value)} onKeyDown={e => e.key === 'Enter' && save()} /></div>
          <div className="grid gap-2"><Label htmlFor="tpl-desc">{t('templates.description')}</Label>
            <Textarea id="tpl-desc" value={desc} maxLength={500} rows={3} onChange={e => setDesc(e.target.value)} /></div>
          {can(me, 'org.manage') && <div className="grid gap-2"><Label htmlFor="tpl-scope">{t('templates.visibility')}</Label>
            <Select value={scope} onValueChange={v => setScope(v as 'user' | 'org')}><SelectTrigger id="tpl-scope" className="w-full"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="user">{t('templates.scope.user')}</SelectItem><SelectItem value="org">{t('templates.scope.org')}</SelectItem></SelectContent></Select></div>}
          {err && <Alert variant="destructive" id="tpl-save-error"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
        </>}
        </DialogBody>
        <DialogFooter>
          {done ? <Button onClick={() => setOpen(false)}>{t('common.close')}</Button> : <>
            <Button variant="outline" onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
            <Button id="tpl-save" onClick={save} disabled={!name.trim() || busy}>{busy && <Loader2 className="animate-spin" />}{t('templates.saveAsConfirm')}</Button></>}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
