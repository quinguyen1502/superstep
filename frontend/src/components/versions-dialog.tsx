import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'
import { AlertCircle, History, Info, RotateCcw, TriangleAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useOpenState } from '@/lib/use-open-state'
import { api } from '@/lib/api'
import { fmtDate } from '@/lib/i18n'
import i18n from '@/lib/i18n'
import { useLoadWhen } from '@/lib/use-when'

type Version = { version: number; name: string; created: number; author_email: string | null; note: string | null; node_count: number; current: boolean }
type Child = { id: string; name: string; version: number; at: number }
type Page = { items: Version[]; total: number; limit: number; offset: number; children_changed?: Child[] }
const PAGE = 20
type Section = { added: any[]; removed: any[]; changed: { id: string; fields: string[]; before: any; after: any }[]; moved?: string[] }
type Diff = { a: number; b: number; identical: boolean; name: { before: string; after: string } | null; nodes: Section; edges: Section; state: Section }

const label = (x: any) => x.id ?? x.name ?? '?'
const edgeLabel = (e: any) => `${e.source} → ${e.target}${e.label ? ` (${e.label})` : ''}`

function SectionView({ title, s, kind }: { title: string; s: Section; kind: 'nodes' | 'edges' | 'state' }) {
  const { t } = useTranslation()
  const name = (x: any) => kind === 'edges' ? edgeLabel(x) : `${label(x)}${x.type ? ` · ${x.type}` : ''}`
  const rows = [
    ...s.added.map(x => ({ k: `+${label(x)}`, v: 'success' as const, tag: t('versions.added'), text: name(x) })),
    ...s.removed.map(x => ({ k: `-${label(x)}`, v: 'destructive' as const, tag: t('versions.removed'), text: name(x) })),
    ...s.changed.map(c => ({ k: `~${c.id}`, v: 'warning' as const, tag: t('versions.changed'), text: `${c.id}: ${c.fields.join(', ')}`, c })),
    ...(s.moved ?? []).map(id => ({ k: `>${id}`, v: 'secondary' as const, tag: t('versions.moved'), text: id })),
  ]
  if (!rows.length) return null
  return <div className="space-y-1">
    <div className="text-xs font-medium text-muted-foreground">{title}</div>
    {rows.map(r => <div key={r.k} data-testid="diff-row" className="text-xs space-y-1">
      <div className="flex items-center gap-2"><Badge variant={r.v}>{r.tag}</Badge><span className="font-mono">{r.text}</span></div>
      {'c' in r && r.c && <div className="grid grid-cols-2 gap-2 pl-2">
        <pre className="rounded bg-muted p-1.5 overflow-auto max-h-32 text-[11px]">{JSON.stringify(r.c.before, null, 1)}</pre>
        <pre className="rounded bg-muted p-1.5 overflow-auto max-h-32 text-[11px]">{JSON.stringify(r.c.after, null, 1)}</pre></div>}
    </div>)}
  </div>
}

/** Workflow version history: list, diff any two versions, restore (TASK-0008). */
export function VersionsDialog(props: { wid?: string; onRestored: (wf: any) => void; isDirty?: () => boolean; open?: boolean; onOpenChange?: (v: boolean) => void }) {
  const { wid, onRestored, isDirty } = props
  const { t } = useTranslation(); const [open, setOpen, controlled] = useOpenState(props.open, props.onOpenChange)
  const [items, setItems] = useState<Version[]>([]); const [err, setErr] = useState('')
  const [a, setA] = useState<string>(''); const [b, setB] = useState<string>(''); const [diff, setDiff] = useState<Diff | null>(null)
  const [confirm, setConfirm] = useState<number | null>(null); const [total, setTotal] = useState(0)
  const [notice, setNotice] = useState(''); const [dirty, setDirty] = useState(false); const [children, setChildren] = useState<Child[]>([])
  const page = (offset: number) => api<Page>(`/api/workflows/${wid}/versions?limit=${PAGE}&offset=${offset}`)
  const load = () => wid && page(0).then(p => {
    setItems(p.items); setTotal(p.total); setChildren(p.children_changed || []); setB(String(p.items[0]?.version ?? '')); setA(String(p.items[1]?.version ?? p.items[0]?.version ?? ''))
  }).catch(e => setErr(e.message))
  const more = () => page(items.length).then(p => { setItems(xs => [...xs, ...p.items]); setTotal(p.total) }).catch(e => setErr(e.message))
  useLoadWhen(open, () => { setErr(''); setNotice(''); setConfirm(null); setDiff(null); setDirty(!!isDirty?.()); load() })
  useEffect(() => {
    if (!open || !a || !b) return
    api<Diff>(`/api/workflows/${wid}/versions/diff?a=${a}&b=${b}`).then(setDiff).catch(e => setErr(e.message))
  }, [a, b, open, wid])
  const restore = async (n: number) => {
    setErr('')
    try {
      const r = await api<any>(`/api/workflows/${wid}/versions/${n}/restore`, { method: 'POST' }); setConfirm(null)
      if (r.unchanged) { setNotice(t('versions.unchanged', { n })); if (dirty) { onRestored(r.workflow); setDirty(false) }; return }
      setNotice(t('versions.restored', { n })); onRestored(r.workflow); setDirty(false); load()
    }
    catch (e: any) { setErr(e.message) }
  }
  const pick = (v: string, set: (s: string) => void) => <Select value={v} onValueChange={set}>
    <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
    <SelectContent>{items.map(i => <SelectItem key={i.version} value={String(i.version)}>v{i.version}</SelectItem>)}</SelectContent>
  </Select>
  return <Dialog open={open} onOpenChange={setOpen}>
    {!controlled && <DialogTrigger asChild><Button size="sm" variant="outline" id="versions-btn" disabled={!wid}><History />{t('versions.button')}</Button></DialogTrigger>}
    <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-4xl">
      <DialogHeader><DialogTitle>{t('versions.title')}</DialogTitle><DialogDescription>{t('versions.desc')}</DialogDescription></DialogHeader>
      {err && <Alert variant="destructive"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
      {!!children.length && <Alert variant="warning" id="versions-children"><TriangleAlert /><AlertDescription>{t('versions.childrenChanged', { count: children.length })}
        <ul className="mt-1 list-disc pl-4">{children.map(c => <li key={c.id}>{c.name} · v{c.version} · {fmtDate(c.at)}</li>)}</ul></AlertDescription></Alert>}
      {notice && <Alert id="versions-notice"><Info /><AlertDescription>{notice}</AlertDescription></Alert>}
      <div className="grid grid-cols-1 gap-4 min-h-0 sm:grid-cols-[18rem_minmax(0,1fr)]">
        <ScrollArea className="h-48 rounded-md border sm:h-96">
          <div className="p-1">{items.map(v => <div key={v.version} data-testid="version-row" className="rounded-md px-2 py-1.5 text-xs hover:bg-accent space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-mono font-semibold">v{v.version}</span>
              {v.current && <Badge variant="success">{t('versions.current')}</Badge>}
              <span className="ml-auto text-muted-foreground">{new Date(v.created * 1000).toLocaleString(i18n.resolvedLanguage)}</span>
            </div>
            <div className="text-muted-foreground truncate">{v.author_email ?? '—'} · {t('versions.nodes', { count: v.node_count })}</div>
            {v.note && <div className="text-muted-foreground italic truncate">{v.note.startsWith('Restored from v') ? t('versions.restoredFrom', { n: v.note.slice(15) }) : v.note === 'Initial version' ? t('versions.initial') : v.note}</div>}
            {!v.current && (confirm === v.version
              ? <div className="space-y-1">{dirty && <p className="text-warning" data-testid="restore-unsaved-warning">{t('versions.unsavedWarning')}</p>}<div className="flex gap-1"><Button size="xs" variant="destructive" data-testid="restore-confirm" onClick={() => restore(v.version)}>{t('versions.confirm', { n: v.version })}</Button>
                  <Button size="xs" variant="ghost" onClick={() => setConfirm(null)}>{t('common.cancel')}</Button></div></div>
              : <Button size="xs" variant="ghost" data-testid="restore-btn" onClick={() => setConfirm(v.version)}><RotateCcw />{t('versions.restore')}</Button>)}
          </div>)}
          {items.length < total && <Button variant="ghost" size="sm" className="w-full" id="versions-more" onClick={more}>{t('versions.loadMore')} ({t('versions.shown', { shown: items.length, total })})</Button>}</div>
        </ScrollArea>
        <div className="space-y-3 min-w-0">
          <div className="flex items-center gap-2 text-xs"><span>{t('versions.compare')}</span>{pick(a, setA)}<span>→</span>{pick(b, setB)}</div>
          <ScrollArea className="h-48 sm:h-80"><div className="space-y-3 pr-3" id="version-diff">
            {diff?.identical && <div className="text-xs text-muted-foreground">{t('versions.identical')}</div>}
            {diff?.name && <div className="text-xs"><Badge variant="warning">{t('versions.renamed')}</Badge> <span className="font-mono">{diff.name.before} → {diff.name.after}</span></div>}
            {diff && <><SectionView title={t('versions.nodesTitle')} s={diff.nodes} kind="nodes" />
              <SectionView title={t('versions.edgesTitle')} s={diff.edges} kind="edges" />
              <SectionView title={t('versions.stateTitle')} s={diff.state} kind="state" /></>}
          </div></ScrollArea>
        </div>
      </div>
    </DialogContent>
  </Dialog>
}
