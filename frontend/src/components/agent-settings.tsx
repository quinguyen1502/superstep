/** Agent node settings (TASK-0118, REQ-0072): model, prompts, the tools the model may call (MCP, HTTP, built-in,
 *  knowledge base, another workflow: TASK-0136, REQ-0073) and the approval settings for tools that need approval; its fields (`AgentData`) and round limit
 *  (`AgentExecution`) sit in the Config panel's Data and Execution tabs (TASK-0121). The engine is
 *  `backend/app/engine/agents.py` (DEC-0063). */
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowDown, ArrowUp, Database, ExternalLink, Globe, Plug, Plus, TriangleAlert, Workflow, Wrench, X, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { TextLink } from '@/components/text-link'
import { TemplateEditor, type TemplateField } from '@/components/template-editor'
import { ModelPicker } from '@/components/model-picker'
import { HumanApprovalSettings } from '@/components/human-approval-settings'
import { HumanDeadlineSettings } from '@/components/human-deadline-settings'
import type { Credential } from '@/components/credentials-dialog'
import { api } from '@/lib/api'
import type { Channels } from '@/lib/approvals'
import type { KnowledgeBase } from '@/lib/knowledge'
import type { McpList, McpServer } from '@/lib/mcp'
import type { ProviderInfo } from '@/lib/providers'
import { METHODS, PARAM_TYPES, SOURCES, defaultFields, newTool, toolName, type AgentTool, type BuiltinTool, type Schema, type ToolSource } from '@/lib/agent'

const ICONS: Record<ToolSource, LucideIcon> = { mcp: Plug, http: Globe, builtin: Wrench, knowledge: Database, workflow: Workflow }
type Row = { name: string; type: string; description: string; required: boolean }
const rowsOf = (s?: Schema): Row[] => Object.entries(s?.properties || {}).map(([name, p]) =>
  ({ name, type: p?.type || 'string', description: p?.description || '', required: (s?.required || []).includes(name) }))
const schemaOf = (rows: Row[]): Schema => ({ type: 'object',
  properties: Object.fromEntries(rows.filter(r => r.name).map(r => [r.name, { type: r.type, ...(r.description ? { description: r.description } : {}) }])),
  required: rows.filter(r => r.required && r.name).map(r => r.name) })

/** The parameters the model fills for an HTTP tool, as rows (name, type, description, required). */
function ParamsEditor({ id, value, onChange }: { id: string; value?: Schema; onChange: (s: Schema) => void }) {
  const { t } = useTranslation(); const [rows, setRows] = useState<Row[]>(() => rowsOf(value))
  const set = (next: Row[]) => { setRows(next); onChange(schemaOf(next)) }
  const at = (i: number, patch: Partial<Row>) => set(rows.map((r, j) => j === i ? { ...r, ...patch } : r))
  return <div className="space-y-2" id={`${id}-params`}>
    <Label className="text-xs text-muted-foreground">{t('agent.parameters')}</Label>
    {rows.map((r, i) => <div key={i} className="space-y-1.5 rounded-md border p-2" data-testid="agent-param">
      <div className="flex items-center gap-2">
        <Input className="min-w-0 flex-1 font-mono" value={r.name} aria-label={t('agent.paramName')} placeholder={t('agent.paramName')}
          onChange={e => at(i, { name: e.target.value.replace(/[^A-Za-z0-9_]/g, '') })} />
        <Select value={r.type} onValueChange={v => at(i, { type: v })}>
          <SelectTrigger className="w-28" aria-label={t('agent.paramType')}><SelectValue /></SelectTrigger>
          <SelectContent>{PARAM_TYPES.map(x => <SelectItem key={x} value={x}>{x}</SelectItem>)}</SelectContent></Select>
        <Button variant="ghost" size="icon" aria-label={t('agent.removeParam', { name: r.name || i + 1 })} onClick={() => set(rows.filter((_, j) => j !== i))}><X /></Button>
      </div>
      <Input value={r.description} aria-label={t('agent.paramDescription')} placeholder={t('agent.paramDescription')} onChange={e => at(i, { description: e.target.value })} />
      <div className="flex items-center gap-2"><Switch id={`${id}-req-${i}`} size="sm" checked={r.required} onCheckedChange={c => at(i, { required: c })} />
        <Label htmlFor={`${id}-req-${i}`} className="text-xs font-normal text-muted-foreground">{t('agent.paramRequired')}</Label></div>
    </div>)}
    <Button variant="outline" size="sm" id={`${id}-add-param`} onClick={() => set([...rows, { name: `param${rows.length + 1}`, type: 'string', description: '', required: true }])}><Plus />{t('agent.addParam')}</Button>
  </div>
}

type ToolProps = { tool: AgentTool; index: number; count: number; taken: string[]; fields: TemplateField[]; readOnly?: boolean
  servers: McpServer[] | null; kbs: KnowledgeBase[] | null; builtins: BuiltinTool[]; workflows: Wf[] | null
  onChange: (t: AgentTool) => void; onMove: (by: number) => void; onRemove: () => void }

type Wf = { id: string; name: string; description?: string }
type Field = { name: string; type?: string }

/** A workflow tool (TASK-0136, DEC-0066): which saved workflow runs, the state fields the model fills (parameters) and
 *  the fields of its final state the model gets back (result). The fields come from the workflow's latest version. */
function WorkflowTool({ id, tool, others, workflows, set }: { id: string; tool: AgentTool; others: string[]; workflows: Wf[] | null; set: (p: Partial<AgentTool>) => void }) {
  const { t } = useTranslation(); const [fields, setFields] = useState<Field[] | null>(null)
  useEffect(() => {
    if (!tool.workflow_id) { setFields(null); return }
    api<{ state?: Field[] }>(`/api/workflows/${tool.workflow_id}`).then(w => setFields(w.state || [])).catch(() => setFields([]))
  }, [tool.workflow_id])
  const missing = !!tool.workflow_id && !!workflows && !workflows.some(w => w.id === tool.workflow_id)
  const pick = (wid: string) => {
    const w = workflows?.find(x => x.id === wid)
    api<{ state?: Field[] }>(`/api/workflows/${wid}`).then(full => {
      const names = (full.state || []).map(f => f.name)
      set({ workflow_id: wid, name: toolName((w?.name || 'workflow').toLowerCase(), others), description: tool.description || w?.description || w?.name || '', ...defaultFields(names) })
    }).catch(() => set({ workflow_id: wid }))
  }
  const toggle = (key: 'inputs' | 'outputs', f: string, on: boolean) => {
    const cur = tool[key] || []; set({ [key]: on ? [...cur.filter(x => x !== f), f] : cur.filter(x => x !== f) })
  }
  return <>
    <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={`${id}-workflow`}>{t('agent.workflow')}</Label>
      <Select value={tool.workflow_id || undefined} onValueChange={pick}>
        <SelectTrigger className="w-full" id={`${id}-workflow`}><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
        <SelectContent>{(workflows || []).map(w => <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>)}</SelectContent></Select>
      {!tool.workflow_id && <p className="text-[11px] text-destructive" id={`${id}-workflow-required`}>{t('agent.workflowRequired')}</p>}
      {missing && <p className="text-[11px] text-destructive">{t('editor.subgraphMissing')}</p>}
      {workflows && !workflows.length && <p className="text-[11px] text-muted-foreground">{t('editor.subgraphNone')} <TextLink to="/workflows">{t('editor.subgraphCreate')}</TextLink></p>}
      <p className="text-[11px] text-muted-foreground">{t('agent.workflowHint')}</p></div>
    {fields && fields.length > 0 && <div className="space-y-1" id={`${id}-fields`}>
      <div className="grid grid-cols-[minmax(0,1fr)_72px_72px] items-center gap-2 text-[11px] text-muted-foreground">
        <span>{t('agent.workflowField')}</span><span className="text-center">{t('agent.workflowInput')}</span><span className="text-center">{t('agent.workflowOutput')}</span></div>
      {fields.map(f => <div key={f.name} className="grid grid-cols-[minmax(0,1fr)_72px_72px] items-center gap-2" data-testid="workflow-tool-field">
        <span className="truncate font-mono text-xs">{f.name} <span className="text-muted-foreground">{f.type || 'string'}</span></span>
        <span className="flex justify-center"><Switch size="sm" id={`${id}-in-${f.name}`} aria-label={t('agent.workflowInputOf', { field: f.name })}
          checked={(tool.inputs || []).includes(f.name)} onCheckedChange={c => toggle('inputs', f.name, c)} /></span>
        <span className="flex justify-center"><Switch size="sm" id={`${id}-out-${f.name}`} aria-label={t('agent.workflowOutputOf', { field: f.name })}
          checked={(tool.outputs || []).includes(f.name)} onCheckedChange={c => toggle('outputs', f.name, c)} /></span>
      </div>)}
      {!(tool.outputs || []).length && <p className="text-[11px] text-destructive" id={`${id}-outputs-required`}>{t('agent.workflowOutputsRequired')}</p>}
      <p className="text-[11px] text-muted-foreground">{t('agent.workflowFieldsHint')}</p></div>}
    {tool.workflow_id && !missing && <Button variant="outline" size="sm" asChild><Link to={`/workflows/${tool.workflow_id}`} id={`${id}-open`}><ExternalLink />{t('editor.subgraphOpen')}</Link></Button>}
  </>
}

function ToolCard({ tool, index, count, taken, fields, readOnly, servers, kbs, builtins, workflows, onChange, onMove, onRemove }: ToolProps) {
  const { t } = useTranslation(); const I = ICONS[tool.source] ?? Wrench; const id = `agent-tool-${index}`
  const set = (patch: Partial<AgentTool>) => onChange({ ...tool, ...patch })
  const others = taken.filter(n => n !== tool.name)
  const server = servers?.find(s => s.id === tool.server_id)
  const tpl = { fields: [...fields, { name: 'args', type: 'object' }], readOnly }
  return <Card className="gap-3 p-3" id={id} data-testid="agent-tool" data-source={tool.source}>
    <div className="flex items-center gap-2">
      <span className="rounded-md bg-muted p-1.5 text-muted-foreground"><I className="size-3.5" /></span>
      <span className="min-w-0 flex-1 truncate text-xs font-medium">{t(`agent.sources.${tool.source}`)}</span>
      <Button variant="ghost" size="icon-xs" aria-label={t('agent.moveUp', { name: tool.name })} disabled={index === 0} onClick={() => onMove(-1)}><ArrowUp /></Button>
      <Button variant="ghost" size="icon-xs" aria-label={t('agent.moveDown', { name: tool.name })} disabled={index === count - 1} onClick={() => onMove(1)}><ArrowDown /></Button>
      <Button variant="ghost" size="icon-xs" aria-label={t('agent.removeTool', { name: tool.name })} id={`${id}-remove`} onClick={onRemove}><X /></Button>
    </div>
    {tool.source === 'mcp' && <>
      <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={`${id}-server`}>{t('editor.mcpServer')}</Label>
        <Select value={tool.server_id || undefined} onValueChange={v => set({ server_id: v, tool: '', parameters: undefined })}>
          <SelectTrigger className="w-full" id={`${id}-server`}><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
          <SelectContent>{(servers || []).map(s => <SelectItem key={s.id} value={s.id}>{s.name} · {s.transport}</SelectItem>)}</SelectContent></Select>
        {servers && !servers.length && <p className="text-[11px] text-muted-foreground">{t('editor.mcpNone')} <TextLink to="/settings/mcp">{t('editor.mcpCreate')}</TextLink></p>}</div>
      {server && <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={`${id}-mcp-tool`}>{t('editor.mcpTool')}</Label>
        <Select value={tool.tool || undefined} onValueChange={v => { const def = server.tools.find(x => x.name === v)
            set({ tool: v, name: toolName(v, others), description: def?.description || '', parameters: { type: 'object', ...(def?.input_schema || {}) } }) }}>
          <SelectTrigger className="w-full" id={`${id}-mcp-tool`}><SelectValue placeholder={server.tools.length ? t('common.choose') : t('editor.mcpNoTools')} /></SelectTrigger>
          <SelectContent>{server.tools.map(x => <SelectItem key={x.name} value={x.name}>{x.name}</SelectItem>)}</SelectContent></Select></div>}
    </>}
    {tool.source === 'builtin' && <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={`${id}-function`}>{t('field.function')}</Label>
      <Select value={tool.function || undefined} onValueChange={v => { const b = builtins.find(x => x.name === v)
          set({ function: v, name: toolName(v, others), description: b?.doc || '' }) }}>
        <SelectTrigger className="w-full" id={`${id}-function`}><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
        <SelectContent>{builtins.map(b => <SelectItem key={b.name} value={b.name}>{b.name}</SelectItem>)}</SelectContent></Select></div>}
    {tool.source === 'knowledge' && <>
      <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={`${id}-kb`}>{t('editor.retrieverKb')}</Label>
        <Select value={tool.knowledge_base_id || undefined} onValueChange={v => { const k = kbs?.find(x => x.id === v)
            set({ knowledge_base_id: v, ...(k && !tool.description ? { description: k.description || k.name } : {}) }) }}>
          <SelectTrigger className="w-full" id={`${id}-kb`}><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
          <SelectContent>{(kbs || []).map(k => <SelectItem key={k.id} value={k.id}>{k.name} · {t('kb.documents', { count: k.documents })}</SelectItem>)}</SelectContent></Select>
        {!tool.knowledge_base_id && <p className="text-[11px] text-destructive" id={`${id}-kb-required`}>{t('editor.retrieverRequired')}</p>}
        {kbs && !kbs.length && <p className="text-[11px] text-muted-foreground">{t('editor.retrieverNone')} <TextLink to="/settings/knowledge">{t('editor.retrieverCreate')}</TextLink></p>}</div>
      <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={`${id}-topk`}>{t('editor.retrieverTopK')}</Label>
        <Input id={`${id}-topk`} type="number" min={1} max={20} value={tool.top_k ?? 4} onChange={e => set({ top_k: Math.max(1, Math.min(20, Number(e.target.value) || 1)) })} />
        <p className="text-[11px] text-muted-foreground">{t('agent.kbHint')}</p></div>
    </>}
    {tool.source === 'workflow' && <WorkflowTool id={id} tool={tool} others={others} workflows={workflows} set={set} />}
    {tool.source === 'http' && <>
      <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">{t('field.method')}</Label>
        <Select value={tool.method || 'GET'} onValueChange={v => set({ method: v })}>
          <SelectTrigger className="w-full" id={`${id}-method`}><SelectValue /></SelectTrigger>
          <SelectContent>{METHODS.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent></Select></div>
      <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">{t('field.url')}</Label>
        <TemplateEditor {...tpl} singleLine id={`${id}-url`} placeholder="https://…" value={tool.url || ''} onChange={v => set({ url: v })} /></div>
      <div className="space-y-1.5"><Label className="text-xs text-muted-foreground">{t('field.bodyTemplate')}</Label>
        <TemplateEditor {...tpl} rows={3} id={`${id}-body`} value={tool.body || ''} onChange={v => set({ body: v })} />
        <p className="text-[11px] text-muted-foreground">{t('agent.httpArgsHint', { arg: '{{state.args.name}}' })}</p></div>
      <ParamsEditor id={id} value={tool.parameters} onChange={parameters => set({ parameters })} />
    </>}
    <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={`${id}-name`}>{t('agent.toolName')}</Label>
      <Input id={`${id}-name`} className="font-mono" value={tool.name} onChange={e => set({ name: e.target.value.replace(/[^A-Za-z0-9_-]/g, '').slice(0, 64) })} />
      {others.includes(tool.name) && <p className="text-[11px] text-destructive">{t('agent.duplicateName')}</p>}</div>
    <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={`${id}-description`}>{t('agent.toolDescription')}</Label>
      <Input id={`${id}-description`} value={tool.description || ''} onChange={e => set({ description: e.target.value })} /></div>
    <div className="flex items-center gap-2">
      <Switch id={`${id}-approval`} size="sm" checked={!!tool.approval} onCheckedChange={c => set({ approval: c || undefined })} />
      <Label htmlFor={`${id}-approval`} className="text-xs font-normal">{t('agent.needsApproval')}</Label>
    </div>
  </Card>
}

const F = ({ label, htmlFor, children }: { label: string; htmlFor?: string; children: React.ReactNode }) =>
  <div className="space-y-1.5"><Label className="text-xs text-muted-foreground" htmlFor={htmlFor}>{label}</Label>{children}</div>

type Patch = (patch: Record<string, any>) => void
type Props = { data: Record<string, any>; fields: TemplateField[]; creds: Credential[]
  providers: ProviderInfo[]; channels: Channels | null; builtins: BuiltinTool[]; readOnly?: boolean; nodeId: string; onChange: Patch; wid?: string }

/** Data tab (TASK-0121): the fields the agent writes its answer and steps to, and the history it reads. */
export function AgentData({ data: d, fieldNames, listFields, onChange }: { data: Record<string, any>; fieldNames: string[]; listFields: string[]; onChange: Patch }) {
  const { t } = useTranslation()
  const optional = (key: string, id: string) => <Select value={d[key] || 'none'} onValueChange={v => onChange({ [key]: v === 'none' ? '' : v })}>
    <SelectTrigger className="w-full" id={id}><SelectValue /></SelectTrigger>
    <SelectContent><SelectItem value="none">{t('agent.none')}</SelectItem>{listFields.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent></Select>
  return <div className="space-y-3" id="agent-data">
    <F label={t('field.outputField')}><Select value={d.output_field || undefined} onValueChange={v => onChange({ output_field: v })}>
      <SelectTrigger className="w-full" id="agent-output"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
      <SelectContent>{fieldNames.filter(Boolean).map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent></Select></F>
    <F label={t('agent.stepsField')} htmlFor="agent-steps-field">{optional('steps_field', 'agent-steps-field')}<p className="text-[11px] text-muted-foreground">{t('agent.stepsHint')}</p></F>
    <F label={t('agent.historyField')} htmlFor="agent-history-field">{optional('history_field', 'agent-history-field')}<p className="text-[11px] text-muted-foreground">{t('agent.historyHint')}</p></F>
  </div>
}

/** Execution tab (TASK-0121): the round limit, above the shared retry / timeout / cache settings. */
export function AgentExecution({ data: d, onChange }: { data: Record<string, any>; onChange: Patch }) {
  const { t } = useTranslation()
  return <F label={t('agent.maxRounds')} htmlFor="agent-max-rounds"><Input id="agent-max-rounds" type="number" min={1} max={25} value={d.max_rounds ?? 5}
    onChange={e => onChange({ max_rounds: e.target.value === '' ? undefined : Math.max(1, Math.min(25, Math.round(Number(e.target.value)) || 1)) })} />
    <p className="text-[11px] text-muted-foreground">{t('agent.maxRoundsHint')}</p></F>
}

/** Settings tab: model, prompts, tools and the approval settings for tools that need approval. */
export function AgentSettings({ data: d, fields, creds, providers, channels, builtins, readOnly, nodeId, onChange, wid }: Props) {
  const { t } = useTranslation()
  const [servers, setServers] = useState<McpServer[] | null>(null); const [kbs, setKbs] = useState<KnowledgeBase[] | null>(null)
  useEffect(() => {
    api<McpList>('/api/mcp/servers').then(x => setServers(x.servers)).catch(() => setServers([]))
    api<KnowledgeBase[]>('/api/knowledge-bases').then(setKbs).catch(() => setKbs([]))
  }, [])
  const [workflows, setWorkflows] = useState<Wf[] | null>(null)  // workflow tools: every workflow but this one
  useEffect(() => { api<Wf[]>('/api/workflows').then(ws => setWorkflows(ws.filter(w => w.id !== wid))).catch(() => setWorkflows([])) }, [wid])
  const tools: AgentTool[] = Array.isArray(d.tools) ? d.tools : []
  const names = tools.map(x => x.name)
  // a stable key per tool card that moves with it, so a card's own state (parameter rows) never shows another tool
  const [keyed, setKeyed] = useState(() => ({ keys: tools.map((_, i) => i), next: tools.length }))
  let keys = keyed.keys
  if (keys.length !== tools.length) {  // the list changed elsewhere (undo, redo, paste): new keys for every card
    const fresh = { keys: tools.map((_, i) => keyed.next + i), next: keyed.next + tools.length }; setKeyed(fresh); keys = fresh.keys }
  const setTools = (next: AgentTool[], nextKeys: number[]) => { setKeyed({ keys: nextKeys, next: Math.max(keyed.next, ...nextKeys.map(k => k + 1)) }); onChange({ tools: next }) }
  const provider = providers.find(p => p.id === creds.find(c => c.id === d.credential_id)?.provider)
  const tpl = { fields, readOnly, placeholder: t('template.placeholder', { open: '{{' }) }
  return <div className="space-y-3" id="agent-settings">
    <F label={t('editor.credential')} htmlFor="agent-credential"><Select value={d.credential_id || 'none'} onValueChange={v => onChange({ credential_id: v === 'none' ? '' : v })}>
      <SelectTrigger className="w-full" id="agent-credential"><SelectValue /></SelectTrigger>
      <SelectContent><SelectItem value="none">{t('editor.credentialDefault')}</SelectItem>
        {creds.map(c => <SelectItem key={c.id} value={c.id}>{c.name} · {c.provider} {c.hint}</SelectItem>)}</SelectContent></Select></F>
    {provider && !provider.supports_tools && <Alert variant="warning" id="agent-no-tool-calling"><TriangleAlert /><AlertDescription className="text-xs">{t('agent.noToolCalling', { provider: provider.label })}</AlertDescription></Alert>}
    <F label={t('field.model')}><ModelPicker idp="agent-model" credentialId={d.credential_id || undefined} value={d.model || ''} onChange={v => onChange({ model: v })} placeholder={provider?.default_model || 'gpt-4o-mini'} /></F>
    <F label={t('agent.systemPrompt', { field: '{{state.field}}' })}><TemplateEditor {...tpl} rows={3} id="agent-system-prompt" value={d.system_prompt || ''} onChange={v => onChange({ system_prompt: v })} /></F>
    <F label={t('agent.taskPrompt', { field: '{{state.field}}' })}><TemplateEditor {...tpl} rows={5} id="agent-prompt" value={d.prompt || ''} onChange={v => onChange({ prompt: v })} /></F>
    <Separator />
    <div className="flex items-center gap-2">
      <Switch id="agent-parallel" size="sm" checked={d.parallel_tool_calls !== false} disabled={readOnly}
        onCheckedChange={c => onChange({ parallel_tool_calls: c === true })} />
      <Label htmlFor="agent-parallel" className="text-xs font-normal">{t('agent.parallelTools')}</Label>
    </div>
    <p className="text-[11px] text-muted-foreground">{t('agent.parallelToolsHint')}</p>
    <div className="flex items-center gap-2">
      <span className="flex-1 text-xs font-semibold uppercase text-muted-foreground">{t('agent.tools')}</span>
      <DropdownMenu><DropdownMenuTrigger asChild disabled={readOnly}><Button variant="outline" size="sm" id="agent-add-tool"><Plus />{t('agent.addTool')}</Button></DropdownMenuTrigger>
        <DropdownMenuContent align="end">{SOURCES.map(s => { const I = ICONS[s]
          return <DropdownMenuItem key={s} id={`agent-add-${s}`} onSelect={() => setTools([...tools, newTool(s, names)], [...keys, keyed.next])}><I />{t(`agent.sources.${s}`)}</DropdownMenuItem> })}</DropdownMenuContent></DropdownMenu>
    </div>
    <p className="text-[11px] text-muted-foreground">{t('agent.toolsHint')}</p>
    {!tools.length && <p className="text-[11px] text-destructive" id="agent-no-tools">{t('agent.noToolsYet')}</p>}
    {tools.map((x, i) => <ToolCard key={keys[i]} tool={x} index={i} count={tools.length} taken={names} fields={fields} readOnly={readOnly}
      servers={servers} kbs={kbs} builtins={builtins} workflows={workflows}
      onChange={nx => setTools(tools.map((y, j) => j === i ? nx : y), keys)}
      onMove={by => { const move = <T,>(xs: T[]) => { const next = [...xs]; const [it] = next.splice(i, 1); next.splice(i + by, 0, it); return next }
        setTools(move(tools), move(keys)) }}
      onRemove={() => setTools(tools.filter((_, j) => j !== i), keys.filter((_, j) => j !== i))} />)}
    {tools.some(x => x.approval) && <>
      <p className="text-[11px] text-muted-foreground" id="agent-approval-hint">{t('agent.approvalHint')}</p>
      <HumanApprovalSettings key={`${nodeId}-approval`} value={d.approval} channels={channels} onChange={v => onChange({ approval: v })} />
      <HumanDeadlineSettings key={`${nodeId}-deadline`} value={d.deadline} onChange={v => onChange({ deadline: v })} />
    </>}
  </div>
}
