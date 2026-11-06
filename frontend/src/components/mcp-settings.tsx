/** MCP tool node settings (TASK-0013): server, tool (from the last discovery) and one input per tool argument. */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ExternalLink, RefreshCw } from 'lucide-react'
import { TextButton, TextLink } from '@/components/text-link'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { TemplateEditor, type TemplateField } from '@/components/template-editor'
import { api } from '@/lib/api'
import type { McpList, McpServer } from '@/lib/mcp'

type Props = { hideArguments?: boolean; recipeConnection?: string; server?: string; tool?: string; args?: Record<string, any>; fields: TemplateField[]; readOnly?: boolean; onChange: (patch: Record<string, any>) => void }

export function McpSettings({ server, tool, args = {}, fields, readOnly, onChange, hideArguments, recipeConnection }: Props) {
  const { t } = useTranslation(); const [items, setItems] = useState<McpServer[] | null>(null); const [err, setErr] = useState('')
  useEffect(() => { api<McpList>('/api/mcp/servers').then(d => setItems(d.servers)).catch(e => { setItems([]); setErr(e.message) }) }, [])
  const s = items?.find(x => x.id === server)
  const def = s?.tools.find(x => x.name === tool)
  const props = Object.entries(def?.input_schema?.properties || {}); const req = def?.input_schema?.required || []
  const discover = () => { setErr(''); api<McpServer>(`/api/mcp/servers/${server}/discover`, { method: 'POST' })
    .then(d => setItems(xs => (xs || []).map(x => x.id === d.id ? d : x))).catch(e => setErr(e.message)) }
  const asText = (v: any) => v === undefined ? '' : typeof v === 'string' ? v : JSON.stringify(v)
  return <div className="space-y-3" id="mcp-settings">
    <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor="mcp-server">{t('editor.mcpServer')}</Label>
      <Select disabled={!!recipeConnection} value={server || ''} onValueChange={v => onChange({ server_id: v, tool: '', arguments: {} })}>
        <SelectTrigger className="w-full" id="mcp-server"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
        <SelectContent emptyMessage={err || (items === null ? t('common.loading') : undefined)}>{(items || []).map(x => <SelectItem key={x.id} value={x.id}>{x.name} · {x.transport}</SelectItem>)}</SelectContent>
      </Select></div>
    {server && items && !s && <p className="text-[11px] text-destructive">{t('editor.mcpMissing')}</p>}
    {items && !items.length && <p className="text-[11px] text-muted-foreground" id="mcp-none">{t('editor.mcpNone')} <TextLink to="/settings/mcp" id="mcp-create">{t('editor.mcpCreate')}</TextLink></p>}
    {s && <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor="mcp-tool">{t('editor.mcpTool')}</Label>
      <div className="flex gap-2">
        <Select value={tool || ''} onValueChange={v => onChange({ tool: v, arguments: {}, target: undefined, targets: undefined })}>
          <SelectTrigger className="w-full min-w-0" id="mcp-tool"><SelectValue placeholder={s.tools.length ? t('common.choose') : t('editor.mcpNoTools')} /></SelectTrigger>
          <SelectContent>{s.tools.map(x => <SelectItem key={x.name} value={x.name}>{x.name}</SelectItem>)}</SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={discover} aria-label={t('mcp.discover')} id="mcp-refresh"><RefreshCw /></Button>
      </div>
      {!s.tools.length && <p className="text-[11px] text-muted-foreground">{t('editor.mcpNoTools')} <TextButton id="mcp-refresh-link" onClick={discover}>{t('editor.mcpRefresh')}</TextButton></p>}
      {def?.description && <p className="text-[11px] text-muted-foreground" id="mcp-tool-desc">{def.description}</p>}
    </div>}
    {err && <p className="text-[11px] text-destructive">{err}</p>}
    {!hideArguments && props.length > 0 && <div className="space-y-2" id="mcp-args">
      <p className="text-xs font-medium">{t('editor.mcpArgs')}</p>
      {props.map(([name, p]) => <div key={name} className="space-y-1">
        <Label className="text-xs text-muted-foreground" htmlFor={`mcp-arg-${name}`}>{name}{req.includes(name) && ' *'} <span className="font-mono text-[10px]">{p.type}</span></Label>
        <TemplateEditor singleLine id={`mcp-arg-${name}`} fields={fields} readOnly={readOnly} value={asText(args[name])} placeholder={p.description || '{{state.field}}'}
          onChange={v => onChange({ arguments: { ...args, [name]: v } })} />
      </div>)}
      <p className="text-[11px] text-muted-foreground">{t('editor.mcpArgsHint', { field: '{{state.field}}' })}</p>
    </div>}
    <Button variant="outline" asChild><Link to="/settings/mcp" id="mcp-manage"><ExternalLink /><span>{t('editor.mcpManage')}</span></Link></Button>
  </div>
}
