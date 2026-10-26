import { useState, type ReactNode } from 'react'
import { Sparkles } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tip } from '@/components/tip'
import { NodeInput } from '@/components/node-input'
import { NodeRuntime } from '@/components/node-runtime'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { applyMode, codeChoices, modeValue, nodeLanguage, type ToolModeValue } from '@/lib/code-mode'
import { api } from '@/lib/api'
import { useTranslation } from 'react-i18next'
import { ANSWERED_BY } from '@/lib/chat'
import { HumanApprovalSettings } from '@/components/human-approval-settings'
import { HumanDeadlineSettings } from '@/components/human-deadline-settings'
import { CredentialsDialog, type Credential } from '@/components/credentials-dialog'
import { TextButton } from '@/components/text-link'
import { ModelPicker } from '@/components/model-picker'
import { SubgraphSettings } from '@/components/subgraph-settings'
import { RetrieverSettings } from '@/components/retriever-settings'
import { McpSettings } from '@/components/mcp-settings'
import { AgentData, AgentExecution, AgentSettings } from '@/components/agent-settings'
import { DecisionData, DecisionSettings } from '@/components/decision-settings'
import { EmailData, EmailSettings } from '@/components/email-settings'
import { TemplateEditor } from '@/components/template-editor'
import { CodeSettings } from '@/components/code-settings'
import { codeOffKey, useCodeRuntime } from '@/lib/code-runtime'
import { can, useMe } from '@/lib/rbac'
import { META, RUNTIME, LOOP_LABELS } from './meta'
import { Sel, F } from './parts'
import { useStudioCtx } from './studio-context'

/** Config tabs (TASK-0121): the same three, in the same order, for every node, so a setting is always found in one place.
 *  Settings: what the node does. Data: every picker of a state field (what it reads and writes, which fields it sees).
 *  Execution: how it runs (retry, timeout, cache, limits). A tab a node does not use stays in its place, disabled. */
const CONFIG_TABS = ['settings', 'data', 'execution'] as const
type ConfigTab = typeof CONFIG_TABS[number]
const FIELD_PICKERS = new Set(['email', 'decision', 'condition', 'foreach'])  // state fields picked besides RUNTIME's input fields
const LIMITS = new Set(['foreach'])  // an execution limit without RUNTIME's retry / timeout / cache
const WRITERS = new Set(['llm', 'tool', 'human', 'retriever', 'mcp', 'agent'])  // output_field required (backend engine/validator.py)

/** Right panel: config of the selected node or edge (TASK-0040). */
export function EditorConfig() {
  const [kept, setKept] = useState<string | null>(null)  // node whose edited code was kept on a language switch
  const [tab, setTab] = useState<ConfigTab>('settings')  // kept while another node is selected
  const { t } = useTranslation()
  const { nodes, setEdges, wid, tools, creds, setCreds, providers, channels, edit, mark, selNode, selEdge, upd, setRuntime, d, fieldNames, state, input } = useStudioCtx()
  const codeRt = useCodeRuntime(); const canCode = can(useMe(), 'code.write')  // Tool node Code mode (TASK-0055)
  const chatCreds = creds.filter(c => (providers.find(p => p.id === c.provider)?.kind ?? 'chat') === 'chat')  // TypeSafe keys: Decision nodes; SMTP: Send email
  const tpl = { fields: state, readOnly: !edit, placeholder: t('template.placeholder', { open: '{{' }) }
  const type = selNode?.type || ''
  const node = !!selNode && type !== 'note'
  const runtime = RUNTIME.has(type)
  const has: Record<ConfigTab, boolean> = { settings: type !== 'start' && type !== 'end', data: runtime || FIELD_PICKERS.has(type), execution: runtime || LIMITS.has(type) }
  const issue: Record<ConfigTab, boolean> = { settings: type === 'agent' && !(Array.isArray(d.tools) && d.tools.length), data: WRITERS.has(type) && !d.output_field, execution: false }
  const enabled = CONFIG_TABS.filter(k => has[k])
  const active = enabled.includes(tab) ? tab : enabled[0]
  const output = <F label={t('field.outputField')}><Sel value={d.output_field} onChange={v => upd('output_field', v)} opts={fieldNames} /></F>
  const pane = (k: ConfigTab, children: ReactNode) => <TabsContent value={k} className="space-y-3" id={`config-pane-${k}`}>{children}</TabsContent>

  const settings = <>
    {type === 'llm' && <>
      <F label={t('editor.credential')}><Select value={d.credential_id || 'none'} onValueChange={v => upd('credential_id', v === 'none' ? '' : v)}>
        <SelectTrigger className="w-full" id="llm-credential"><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="none">{t('editor.credentialDefault')}</SelectItem>
          {chatCreds.map(c => <SelectItem key={c.id} value={c.id}>{c.name} · {c.provider} {c.hint}</SelectItem>)}</SelectContent></Select>
        {!chatCreds.length && <p className="text-[11px] text-muted-foreground" id="llm-no-credential">{t('editor.credentialNone')} <CredentialsDialog onChanged={() => { api<Credential[]>('/api/credentials').then(setCreds).catch(() => {}) }} trigger={<TextButton id="llm-add-credential">{t('editor.credentialAdd')}</TextButton>} /></p>}</F>
      <F label={t('field.model')}><ModelPicker credentialId={d.credential_id || undefined} value={d.model || ''} onChange={v => upd('model', v)} placeholder={providers.find(p => p.id === creds.find(c => c.id === d.credential_id)?.provider)?.default_model || 'gpt-4o-mini'} /></F>
      <F label={t('field.promptTemplate', { field: '{{state.field}}' })}><TemplateEditor {...tpl} rows={7} id="llm-prompt" value={d.prompt || ''} onChange={v => upd('prompt', v)} /></F>
    </>}
    {type === 'agent' && selNode && <AgentSettings key={selNode.id} wid={wid} data={d} nodeId={selNode.id} fields={state} creds={chatCreds} providers={providers} channels={channels}
      builtins={tools} readOnly={!edit} onChange={p => mark(selNode.id, p)} />}
    {type === 'human' && selNode && <>
      <F label={t('field.humanPrompt', { field: '{{state.field}}' })}><TemplateEditor {...tpl} rows={4} id="human-prompt" value={d.prompt || ''} onChange={v => upd('prompt', v)} /></F>
      <F label={t('chat.answeredBy')}><Select value={d.answered_by || 'visitor'} onValueChange={v => upd('answered_by', v)} disabled={!edit}>
        <SelectTrigger className="w-full" id="human-answered-by"><SelectValue /></SelectTrigger>
        <SelectContent>{ANSWERED_BY.map(a => <SelectItem key={a} value={a}>{t(`chat.answeredByOpt.${a}`)}</SelectItem>)}</SelectContent></Select>
        <p className="text-[11px] text-muted-foreground" id="human-answered-by-hint">{t(`chat.answeredByHint.${d.answered_by || 'visitor'}`)}</p></F>
      <HumanApprovalSettings key={selNode.id} value={d.approval} channels={channels} onChange={v => upd('approval', v)} />
      <HumanDeadlineSettings key={`${selNode.id}-deadline`} value={d.deadline} onChange={v => upd('deadline', v)} />
    </>}
    {type === 'tool' && selNode && <>
      <F label={t('field.mode')}><Select value={modeValue(d)} onValueChange={v => { const r = applyMode(d, v as ToolModeValue, codeRt); setKept(r.kept ? selNode.id : null); if (Object.keys(r.patch).length) mark(selNode.id, r.patch) }}>
        <SelectTrigger className="w-full min-w-0" id="tool-mode"><SelectValue className="min-w-0 truncate" /></SelectTrigger>
        <SelectContent><SelectItem value="function">{t('editor.pyFunction')}</SelectItem><SelectItem value="http">{t('editor.httpRequest')}</SelectItem>
          {codeChoices(codeRt, d).map(l => <SelectItem key={l} value={`code:${l}`} id={`tool-mode-code-${l}`} disabled={d.mode !== 'code' && (!canCode || codeRt?.code_runtime === 'off')}>
            {t('editor.codeMode', { language: t(`code.languages.${l}`) })}
            {codeRt?.code_runtime === 'subprocess' && <Tip tip={t('code.notIsolatedTip')}><Badge variant="warning" size="sm" className="ml-1 min-w-0 shrink truncate" data-testid="mode-unisolated">{t('code.notIsolatedShort')}</Badge></Tip>}</SelectItem>)}</SelectContent></Select>
        {d.mode !== 'code' && !canCode && <p className="text-[11px] text-muted-foreground" id="tool-code-locked">{t('code.locked')}</p>}
        {d.mode !== 'code' && canCode && codeRt?.code_runtime === 'off' && <p className="text-[11px] text-muted-foreground" id="tool-code-off">{t(codeOffKey(codeRt))}</p>}</F>
      {d.mode === 'code' ? <F label={t('field.code')}><CodeSettings key={`${selNode.id}-${nodeLanguage(d)}`} value={d.code || ''} onChange={v => upd('code', v)} runtime={codeRt} canWrite={canCode}
          editable={edit} input={input} nodeId={selNode.id} timeout={typeof d.timeout === 'number' ? d.timeout : undefined}
          language={nodeLanguage(d)} fields={state} kept={kept === selNode.id} /></F>
      : d.mode === 'http' ? <>
        <F label={t('field.method')}><Sel value={d.method} onChange={v => upd('method', v)} opts={['GET', 'POST', 'PUT', 'DELETE']} /></F>
        <F label={t('field.url')}><TemplateEditor {...tpl} singleLine id="http-url" placeholder="https://…" value={d.url || ''} onChange={v => upd('url', v)} /></F>
        <F label={t('field.bodyTemplate')}><TemplateEditor {...tpl} rows={4} id="http-body" value={d.body || ''} onChange={v => upd('body', v)} /></F>
      </> : <F label={t('field.function')}><Sel value={d.function} onChange={v => upd('function', v)} opts={tools.map(t => t.name)} /></F>}
    </>}
    {type === 'code' && <>
      <div className="flex flex-wrap gap-1">{d.is_llm && <Badge variant="outline" className="gap-1"><Sparkles className="size-3" />{t('editor.looksLlm')}</Badge>}{d.kind && <Badge variant="secondary">{d.kind}</Badge>}<Badge variant="outline">{t('editor.readOnly')}</Badge></div>
      <F label={t('field.nodeName')}><Input readOnly value={d.node_name || ''} className="font-mono text-xs" /></F>
      <F label={t('field.reference')}><Input readOnly value={d.ref || ''} className="font-mono text-xs" /></F>
      <F label={t('field.source')}><pre className="h-72 w-full overflow-auto rounded-md border bg-muted/50 p-2 text-[11px] leading-relaxed whitespace-pre">{d.source}</pre></F>
    </>}
    {type === 'retriever' && <>
      <RetrieverSettings kb={d.knowledge_base_id} topK={d.top_k} onKb={v => upd('knowledge_base_id', v)} onTopK={v => upd('top_k', v)} />
      <F label={t('field.queryTemplate', { field: '{{state.field}}' })}><TemplateEditor {...tpl} rows={3} id="retriever-query" value={d.query || ''} onChange={v => upd('query', v)} /></F>
    </>}
    {type === 'mcp' && selNode && <McpSettings server={d.server_id} tool={d.tool} args={d.arguments} fields={state} readOnly={!edit} onChange={p => mark(selNode.id, p)} />}
    {type === 'subgraph' && <SubgraphSettings wid={wid} value={d.workflow_id} onChange={v => upd('workflow_id', v)} />}
    {type === 'join' && <p className="text-[11px] text-muted-foreground" id="join-hint">{t('editor.joinHint')}</p>}
    {type === 'condition' && <>
      <F label={t('editor.condDefault')}><Input value={d.default || ''} onChange={e => upd('default', e.target.value)} /></F>
      <p className="text-[11px] text-muted-foreground">{t('editor.condHint')}</p>
    </>}
    {type === 'email' && selNode && <EmailSettings data={d} fields={state} creds={creds} providers={providers} readOnly={!edit} onChange={p => mark(selNode.id, p)} />}
    {type === 'decision' && selNode && <DecisionSettings data={d} fields={state} creds={creds} providers={providers} readOnly={!edit} onChange={p => mark(selNode.id, p)} />}
    {type === 'foreach' && <p className="text-[11px] text-muted-foreground" id="loop-hint">{t('editor.loopHint')}</p>}
  </>

  const data = <>
    {['llm', 'human', 'tool', 'retriever', 'mcp'].includes(type) && output}
    {type === 'agent' && selNode && <AgentData data={d} fieldNames={fieldNames} listFields={state.filter(f => f.type === 'list').map(f => f.name)} onChange={p => mark(selNode.id, p)} />}
    {type === 'email' && selNode && <EmailData data={d} fields={state} onChange={p => mark(selNode.id, p)} />}
    {type === 'decision' && selNode && <DecisionData data={d} fields={state} onChange={p => mark(selNode.id, p)} />}
    {type === 'condition' && <F label={t('editor.condField')}><Sel value={d.field} onChange={v => upd('field', v)} opts={fieldNames} /></F>}
    {type === 'foreach' && <>
      <F label={t('editor.loopItems')}><Sel value={d.items_field} onChange={v => upd('items_field', v)} opts={state.filter(f => f.type === 'list').map(f => f.name)} /></F>
      <F label={t('editor.loopItem')}><Sel value={d.item_field} onChange={v => upd('item_field', v)} opts={state.filter(f => !f.reducer || f.reducer === 'replace').map(f => f.name)} /></F>
      <F label={t('editor.loopIndex')}><Select value={d.index_field || 'none'} onValueChange={v => upd('index_field', v === 'none' ? '' : v)}>
        <SelectTrigger className="w-full" id="loop-index"><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="none">{t('editor.loopIndexNone')}</SelectItem>
          {state.filter(f => (f.type === 'integer' || f.type === 'number') && (!f.reducer || f.reducer === 'replace')).map(f => <SelectItem key={f.name} value={f.name}>{f.name}</SelectItem>)}</SelectContent></Select></F>
    </>}
    {runtime && <NodeInput fields={fieldNames} value={d.input_fields} onChange={input_fields => setRuntime({ input_fields })} />}
  </>

  const execution = <>
    {type === 'agent' && selNode && <AgentExecution data={d} onChange={p => mark(selNode.id, p)} />}
    {type === 'foreach' && <F label={t('editor.loopMax')}><Input id="loop-max" type="number" min={1} max={1000} value={d.max_items ?? 100} onChange={e => upd('max_items', e.target.value === '' ? undefined : Number(e.target.value))} /></F>}
    {runtime && <NodeRuntime data={d} onChange={setRuntime} />}
  </>

  const title = <div className="text-xs font-semibold uppercase text-muted-foreground">{t('editor.config')}</div>
  if (!node) return <aside className="h-full bg-muted/30 min-h-0" id="config-panel">
      <ScrollArea className="h-full"><fieldset disabled={!edit} className="contents"><div className="p-4 space-y-4 min-w-0">
        {title}
        {!selNode && !selEdge && <p className="text-muted-foreground text-xs">{t('editor.selectHint')}</p>}
        {selNode?.type === 'note' && <p className="text-muted-foreground text-xs" id="note-hint">{t('editor.noteHint')}</p>}
        {selEdge && <div className="space-y-3">
          <Badge variant="outline">Edge {selEdge.source} → {selEdge.target}</Badge>
          {nodes.find(n => n.id === selEdge.source)?.type === 'foreach'
            ? <F label={t('editor.loopEdge')}><Select value={LOOP_LABELS.includes(String(selEdge.label)) ? String(selEdge.label) : undefined} onValueChange={v => setEdges(es => es.map(x => x.id === selEdge.id ? { ...x, label: v } : x))}>
                <SelectTrigger className="w-full" id="loop-edge"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
                <SelectContent>{LOOP_LABELS.map(l => <SelectItem key={l} value={l}>{t(`editor.loop.${l}`)}</SelectItem>)}</SelectContent></Select></F>
            : <F label={t('editor.edgeLabel')}><Input value={String(selEdge.label || '')} onChange={e => setEdges(es => es.map(x => x.id === selEdge.id ? { ...x, label: e.target.value } : x))} /></F>}
        </div>}
      </div></fieldset></ScrollArea>
    </aside>

  // the node's name and label stay above the tabs; the tab bar sits outside the disabled fieldset so viewers can switch
  const m = META[type]; const I = m.icon
  return <aside className="h-full bg-muted/30 min-h-0 flex flex-col" id="config-panel">
      <fieldset disabled={!edit} className="contents"><div className="shrink-0 p-4 pb-3 space-y-3 min-w-0">
        {title}
        <div className="flex items-center gap-2"><div className={cn('rounded-md p-1.5', m.color)}><I className="size-4" /></div>
          <div><div className="font-medium">{m.label}</div><div className="text-[11px] text-muted-foreground font-mono">{selNode!.id}</div></div></div>
        <F label={t('field.label')}><Input value={d.label || ''} onChange={e => upd('label', e.target.value)} /></F>
      </div></fieldset>
      <Tabs value={active ?? ''} onValueChange={v => setTab(v as ConfigTab)} className="min-h-0 flex-1 gap-0">
        <div className="shrink-0 px-4 pb-3"><TabsList className="w-full" aria-label={t('editor.configTabs.label')} id="config-tabs">
          {CONFIG_TABS.map(k => <TabsTrigger key={k} value={k} id={`config-tab-${k}`} disabled={!has[k]}>
            {t(`editor.configTabs.${k}`)}
            {has[k] && issue[k] && <span className="absolute top-1 right-1 size-1.5 rounded-full bg-destructive" data-testid="config-tab-issue"><span className="sr-only">{t('editor.configTabs.issue')}</span></span>}
          </TabsTrigger>)}
        </TabsList></div>
        <ScrollArea className="min-h-0 flex-1"><fieldset disabled={!edit} className="contents"><div className="px-4 pb-4 min-w-0">
          {!active && <p className="text-muted-foreground text-xs" id="config-nothing">{t('editor.configTabs.nothing')}</p>}
          {pane('settings', settings)}{pane('data', data)}{pane('execution', execution)}
        </div></fieldset></ScrollArea>
      </Tabs>
    </aside>
}
