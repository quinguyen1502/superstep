import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GitFork, Upload, Loader2, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { HandbookLink } from '@/components/handbook-link'

type Job = { id: string; status: string; log: string[]; error: string | null; graphs: { id: string; ref: string; via: string; name: string; nodes: number; edges: number }[]; required_env: string[] }
const STEPS = ['fetching', 'installing', 'inspecting', 'ready']

export function ImportDialog({ enabled = true }: { enabled?: boolean }) {
  const { t } = useTranslation(); const nav = useNavigate()
  const [open, setOpen] = useState(false); const [tab, setTab] = useState('url')
  const [url, setUrl] = useState('https://github.com/langchain-ai/react-agent'); const [branch, setBranch] = useState(''); const [subdir, setSubdir] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [job, setJob] = useState<Job | null>(null); const [err, setErr] = useState(''); const [pick, setPick] = useState('')
  const timer = useRef<number | undefined>(undefined)
  useEffect(() => () => clearInterval(timer.current), [])
  const busy = !!job && !['ready', 'error'].includes(job.status)

  const start = async () => {
    setErr(''); setJob(null); setPick('')
    const fd = new FormData()
    if (tab === 'url') { fd.append('url', url); if (branch) fd.append('branch', branch) } else if (file) fd.append('file', file); else { setErr(t('import.chooseZip')); return }
    if (subdir) fd.append('subdir', subdir)
    try {
      const r = await api('/api/import', { method: 'POST', body: fd })
      setJob({ id: r.job_id, status: 'queued', log: [], error: null, graphs: [], required_env: [] })
      clearInterval(timer.current)
      timer.current = window.setInterval(async () => {
        const j: Job = await api(`/api/import/${r.job_id}`); setJob(j)
        if (j.status === 'ready' || j.status === 'error') { clearInterval(timer.current); if (j.graphs[0]) setPick(j.graphs[0].id); if (j.error) setErr(j.error) }
      }, 800)
    } catch (e: any) { setErr(e.message) }
  }
  const finalize = async () => {
    try { const r = await api(`/api/import/${job!.id}/finalize`, { method: 'POST', json: { graph_id: pick } }); setOpen(false); nav(`/workflows/${r.id}`) }
    catch (e: any) { setErr(e.message) }
  }

  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild><Button variant="outline" id="import-btn"><GitFork />{t('import.button')}</Button></DialogTrigger>
    <DialogContent className="flex max-h-[85dvh] flex-col overflow-hidden sm:max-w-2xl">
      <DialogHeader><DialogTitle>{t('import.title')}</DialogTitle>
        <DialogDescription>{enabled ? t('import.desc') : t('import.disabled')}</DialogDescription></DialogHeader>
      <DialogBody className="space-y-4">
      {!enabled && <Alert variant="warning" id="import-disabled"><ShieldAlert /><AlertDescription className="space-y-1 text-xs">
        <p>{t('import.disabledHelp')}</p>
        <p><HandbookLink id="import-guide" page="operate/import" label={t('docs.setupGuide')} ariaLabel={t('docs.importGuideAria')} /></p>
      </AlertDescription></Alert>}
      {enabled && <Alert variant="warning"><ShieldAlert /><AlertDescription className="text-xs">{t('import.warning')}</AlertDescription></Alert>}
      {enabled && <><Tabs value={tab} onValueChange={setTab}>
        <TabsList><TabsTrigger value="url"><GitFork />{t('import.url')}</TabsTrigger><TabsTrigger value="zip"><Upload />{t('import.zip')}</TabsTrigger></TabsList>
        <TabsContent value="url" className="space-y-3 pt-2">
          <div className="space-y-1.5"><Label>{t('import.repoUrl')}</Label><Input id="import-url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://github.com/owner/repo" /></div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label>{t('import.branch')}</Label><Input value={branch} onChange={e => setBranch(e.target.value)} placeholder="main" /></div>
            <div className="space-y-1.5"><Label>{t('import.subdir')}</Label><Input value={subdir} onChange={e => setSubdir(e.target.value)} placeholder="examples/agent" /></div>
          </div>
        </TabsContent>
        <TabsContent value="zip" className="space-y-3 pt-2">
          <div className="space-y-1.5"><Label>{t('import.file')}</Label><Input type="file" accept=".zip" onChange={e => setFile(e.target.files?.[0] || null)} /></div>
          <div className="space-y-1.5"><Label>{t('import.subdir')}</Label><Input value={subdir} onChange={e => setSubdir(e.target.value)} /></div>
        </TabsContent>
      </Tabs>
      {job && <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs">{STEPS.map((s, i) => { const cur = STEPS.indexOf(job.status); const done = cur > i || job.status === 'ready'
          return <div key={s} className="flex items-center gap-1.5">
            <Badge variant={done ? 'success' : 'outline'} className={cn(cur === i && job.status !== 'ready' && 'border-warning')}>
              {cur === i && busy ? <Loader2 className="size-3 animate-spin" /> : done ? <CheckCircle2 className="size-3" /> : null}{s}</Badge>{i < 3 && <span className="text-muted-foreground">→</span>}</div> })}
          {job.status === 'error' && <Badge variant="destructive">{t('status.error')}</Badge>}</div>
        <ScrollArea className="h-40 rounded-md border bg-muted/40"><pre className="p-2 text-[11px] whitespace-pre-wrap">{job.log.join('\n') || t('import.waiting')}</pre></ScrollArea>
      </div>}
      {err && <Alert variant="destructive" id="import-error"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
      {job?.status === 'ready' && <div className="space-y-2">
        <Label>{t('import.pickGraph', { count: job.graphs.length })}</Label>
        {job.graphs.map(g => <button key={g.id} onClick={() => setPick(g.id)} className={cn('w-full text-left rounded-md border px-3 py-2 text-sm hover:bg-accent', pick === g.id && 'border-primary ring-1 ring-primary')}>
          <div className="font-medium">{g.id} <span className="text-muted-foreground font-normal">· {g.name}</span></div>
          <div className="text-xs text-muted-foreground font-mono">{g.ref} · {g.nodes} nodes · {g.edges} edges · via {g.via}</div></button>)}
        {job.required_env.length > 0 && <p className="text-xs text-muted-foreground">{t('import.requiredEnv')} {job.required_env.map(k => <Badge key={k} variant="outline" className="mr-1">{k}</Badge>)} — {t('import.requiredEnvHint')}</p>}
      </div>}
      </>}
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={() => setOpen(false)}>{t('common.close')}</Button>
        {enabled && (job?.status === 'ready' ? <Button onClick={finalize} disabled={!pick} id="import-create">{t('import.create')}</Button>
          : <Button onClick={start} disabled={busy} id="import-start">{busy && <Loader2 className="animate-spin" />}{t('import.start')}</Button>)}
      </DialogFooter>
    </DialogContent>
  </Dialog>
}
