/** Retriever node settings (TASK-0012): which knowledge base to search and how many chunks to return. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ExternalLink } from 'lucide-react'
import { TextLink } from '@/components/text-link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { api } from '@/lib/api'
import type { KnowledgeBase } from '@/lib/knowledge'

export function RetrieverSettings({ kb, topK, onKb, onTopK }: { kb?: string; topK?: number; onKb: (v: string) => void; onTopK: (v: number) => void }) {
  const { t } = useTranslation(); const [items, setItems] = useState<KnowledgeBase[] | null>(null)
  useEffect(() => { api<KnowledgeBase[]>('/api/knowledge-bases').then(setItems).catch(() => setItems([])) }, [])
  const missing = kb && items && !items.some(k => k.id === kb)
  return <div className="space-y-3" id="retriever-settings">
    <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor="retriever-kb">{t('editor.retrieverKb')}</Label>
      <Select value={kb || undefined} onValueChange={onKb}>
        <SelectTrigger className="w-full" id="retriever-kb"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
        <SelectContent>{(items || []).map(k => <SelectItem key={k.id} value={k.id}>{k.name} · {t('kb.documents', { count: k.documents })}</SelectItem>)}</SelectContent>
      </Select></div>
    {!kb && <p className="text-[11px] text-destructive" id="retriever-required">{t('editor.retrieverRequired')}</p>}
    {missing && <p className="text-[11px] text-destructive">{t('editor.retrieverMissing')}</p>}
    {items && !items.length && <p className="text-[11px] text-muted-foreground" id="retriever-none">{t('editor.retrieverNone')} <TextLink to="/settings/knowledge" id="retriever-create">{t('editor.retrieverCreate')}</TextLink></p>}
    <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor="retriever-topk">{t('editor.retrieverTopK')}</Label>
      <Input id="retriever-topk" type="number" min={1} max={20} value={topK ?? 4} onChange={e => onTopK(Math.max(1, Math.min(20, Number(e.target.value) || 1)))} /></div>
    <Button variant="outline" size="sm" asChild><Link to="/settings/knowledge" id="retriever-manage"><ExternalLink />{t('editor.retrieverManage')}</Link></Button>
  </div>
}
