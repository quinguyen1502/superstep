import { type Edge } from '@xyflow/react'
import { Keyboard, MessagesSquare, Redo2, Undo2, Play, Save, Brain, Wrench, GitBranch, Flag, CirclePlay, Trash2, Code2, UserCheck, Merge, Layers, Database, Plug, type LucideIcon, CopyPlus, Network, Maximize, Copy, Scissors, ClipboardPaste, BoxSelect, ZoomIn, ZoomOut, Square, Repeat, Scale, Mail, Bot } from 'lucide-react'
import i18n from '@/lib/i18n'

export type Field = { name: string; type: string; reducer?: string }
export type LogItem = { type: string; node?: string; label?: string; duration_ms?: number; delta?: any; state?: any; errors?: string[]; error?: any }
/** `desc` is resolved via i18n key `nodes.<type>`. */
export const META: Record<string, { label: string; icon: LucideIcon; color: string; accent: string }> = {
  start: { label: 'Start', icon: CirclePlay, color: 'bg-node-start-muted text-node-start', accent: 'bg-node-start' },
  llm: { label: 'LLM', icon: Brain, color: 'bg-node-llm-muted text-node-llm', accent: 'bg-node-llm' },
  tool: { label: 'Tool/API', icon: Wrench, color: 'bg-node-tool-muted text-node-tool', accent: 'bg-node-tool' },
  condition: { label: 'Condition', icon: GitBranch, color: 'bg-node-condition-muted text-node-condition', accent: 'bg-node-condition' },
  end: { label: 'End', icon: Flag, color: 'bg-node-end-muted text-node-end', accent: 'bg-node-end' },
  human: { label: 'Human', icon: UserCheck, color: 'bg-node-human-muted text-node-human', accent: 'bg-node-human' },
}
META.join = { label: 'Join', icon: Merge, color: 'bg-node-join-muted text-node-join', accent: 'bg-node-join' }
META.subgraph = { label: 'Subgraph', icon: Layers, color: 'bg-node-subgraph-muted text-node-subgraph', accent: 'bg-node-subgraph' }
META.subgraph_exit = META.subgraph
META.mcp = { label: 'MCP tool', icon: Plug, color: 'bg-node-mcp-muted text-node-mcp', accent: 'bg-node-mcp' }
META.retriever = { label: 'Retriever', icon: Database, color: 'bg-node-retriever-muted text-node-retriever', accent: 'bg-node-retriever' }
META.foreach = { label: 'For each', icon: Repeat, color: 'bg-node-foreach-muted text-node-foreach', accent: 'bg-node-foreach' }
META.decision = { label: 'Decision (Jev)', icon: Scale, color: 'bg-node-decision-muted text-node-decision', accent: 'bg-node-decision' }
META.email = { label: 'Send email', icon: Mail, color: 'bg-node-email-muted text-node-email', accent: 'bg-node-email' }
META.code = { label: 'Code', icon: Code2, color: 'bg-node-code-muted text-node-code', accent: 'bg-node-code' }
META.agent = { label: 'Agent', icon: Bot, color: 'bg-node-agent-muted text-node-agent', accent: 'bg-node-agent' }
/** An Agent node's expanded steps (TASK-0116, DEC-0063) appear in traces only: `ag/__model`, `ag/__tool`, `ag/__exit`. */
META.agent_model = { ...META.agent, icon: Brain }
META.agent_tool = { ...META.agent, icon: Wrench }
META.agent_exit = META.agent
export const TYPES = ['start', 'llm', 'agent', 'decision', 'retriever', 'tool', 'mcp', 'email', 'condition', 'foreach', 'human', 'join', 'subgraph', 'end']
export const INSERTABLE = TYPES.filter(t => t !== 'start' && t !== 'end')
export const RUNTIME = new Set(['llm', 'agent', 'retriever', 'tool', 'mcp', 'human', 'decision'])
/** Reducers per field type (TASK-0011): how parallel writes combine. */
export const REDUCERS: Record<string, string[]> = { list: ['replace', 'append'], object: ['replace', 'merge'], number: ['replace', 'add'], integer: ['replace', 'add'] }
/** Trace events of nodes inside a subgraph carry `sub/inner` ids: the canvas shows them on the subgraph node. */
export const canvasId = (nid: string) => nid.split('/')[0]

/** For each edges (TASK-0049): `each` enters the loop body, `done` leaves after the last item. */
export const LOOP_LABELS = ['each', 'done']

export const styleEdges = (es: any[]): Edge[] => es.map(e => e.conditional ? { ...e, animated: true, style: { strokeDasharray: '6 4' }, labelBgPadding: [6, 3], labelBgBorderRadius: 4 } : e)
export function defaultInput(state: Field[]) {
  return JSON.stringify(Object.fromEntries(state.map(f => [f.name, f.type === 'list' ? [{ role: 'user', content: i18n.t('samples.greeting') }] : f.type === 'number' || f.type === 'integer' ? 0 : f.type === 'boolean' ? false : f.type === 'object' ? {} : 'hello'])), null, 2)
}
export const DEFAULTS: Record<string, any> = {
  start: { label: 'Start' }, end: { label: 'End' },
  llm: { label: 'LLM', model: 'gpt-4o-mini', prompt: '', output_field: '' }, // prompt comes from i18n `samples.prompt` on drop
  agent: { label: 'Agent', model: 'gpt-4o-mini', system_prompt: '', prompt: '', output_field: '', max_rounds: 5, tools: [] }, // prompt: i18n `samples.agentPrompt`
  tool: { label: 'Tool', mode: 'function', function: 'lookup_order', method: 'GET', url: '', body: '', output_field: '' },
  condition: { label: 'Condition', field: '', default: '' },
  decision: { label: 'Decision', credential_id: '', model: 'jev-latest', text: '{{state.message}}', output_field: '',
    questions: [{ id: 'q1', type: 'choice', instructions: '', options: [{ label: '', description: '' }, { label: '', description: '' }], field: '' }] },
  email: { label: 'Send email', credential_id: '', to: '', cc: '', bcc: '', reply_to: '', subject: '', body: '', format: 'text', output_field: '' },
  foreach: { label: 'For each', items_field: '', item_field: '', index_field: '', max_items: 100 },
  human: { label: 'Approval', prompt: '', output_field: '' },
  mcp: { label: 'MCP tool', server_id: '', tool: '', arguments: {}, output_field: '' },
  retriever: { label: 'Retriever', knowledge_base_id: '', query: '{{state.message}}', top_k: 4, output_field: '' },
  join: { label: 'Join' }, subgraph: { label: 'Subgraph', workflow_id: '' }, // response (text, or approved / rejected) goes to output_field
}
/** The prompt a dropped LLM or Agent node starts with, in the UI language. */
export const samplePrompt = (type: string) => type === 'llm' ? { prompt: i18n.t('samples.prompt', { var: '{{state.message}}' }) }
  : type === 'agent' ? { prompt: i18n.t('samples.agentPrompt', { var: '{{state.message}}' }) } : {}

/** Where registry actions appear in the editor's ⋯ menu (others stay keyboard/palette only), with stable ids for tests. */
export const MENU_OF: Record<string, 'arrange' | 'help' | undefined> = { layout: 'arrange', fitView: 'arrange', cheatsheet: 'help' }
export const MENU_IDS: Record<string, string> = { layout: 'layout-btn', fitView: 'fit-btn', cheatsheet: 'shortcuts-btn' }
export const ACTION_ICONS: Record<string, LucideIcon> = { layout: Network, fitView: Maximize, cheatsheet: Keyboard, chat: MessagesSquare, save: Save, run: Play, stop: Square, undo: Undo2, redo: Redo2, delete: Trash2, copy: Copy, cut: Scissors, paste: ClipboardPaste, duplicate: CopyPlus, selectAll: BoxSelect, zoomIn: ZoomIn, zoomOut: ZoomOut }
