/** Subgraph node settings: which saved workflow runs here, with a link to open it. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ExternalLink } from 'lucide-react'
import { TextLink } from '@/components/text-link'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api } from '@/lib/api'

type W = { id: string; name: string; node_count: number }

export function SubgraphSettings({ wid, value, onChange }: { wid?: string; value?: string; onChange: (v: string) => void }) {
  const { t } = useTranslation(); const [items, setItems] = useState<W[] | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { setItems(null); setErr(''); let active = true
    api<W[]>('/api/workflows').then(ws => { if (active) setItems(ws.filter(w => w.id !== wid)) }).catch(e => { if (active) { setItems([]); setErr(e.message) } })
    return () => { active = false }
  }, [wid])
  const missing = value && items && !items.some(w => w.id === value)
  return <div className="space-y-3" id="subgraph-settings">
    <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor="subgraph-workflow">{t('editor.subgraphWorkflow')}</Label>
      <Select value={value || undefined} onValueChange={onChange}>
        <SelectTrigger className="w-full" id="subgraph-workflow"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
        <SelectContent emptyMessage={err || (items === null ? t('common.loading') : undefined)}>{(items || []).map(w => <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>)}</SelectContent>
      </Select></div>
    {missing && <p className="text-[11px] text-destructive">{t('editor.subgraphMissing')}</p>}
    {err && <p role="alert" className="text-xs text-destructive">{err}</p>}
    {items && !items.length && <p className="text-[11px] text-muted-foreground" id="subgraph-none">{t('editor.subgraphNone')} <TextLink to="/workflows" id="subgraph-create">{t('editor.subgraphCreate')}</TextLink></p>}
    <p className="text-[11px] text-muted-foreground">{t('editor.subgraphHint')}</p>
    {value && !missing && <Button variant="outline" size="sm" asChild><Link to={`/workflows/${value}`} id="subgraph-open"><ExternalLink />{t('editor.subgraphOpen')}</Link></Button>}
  </div>
}
