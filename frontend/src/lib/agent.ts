/** Agent node tools: the shapes the settings edit and the engine reads (`engine/agents.py`). */
export const SOURCES = ['mcp', 'http', 'builtin', 'knowledge', 'workflow', 'dataset'] as const
export type ToolSource = typeof SOURCES[number]
export type Schema = { type?: string; properties?: Record<string, { type?: string; description?: string }>; required?: string[] }
import type { UrlBinding } from './browser-tools'
import type { DatasetAgentOperation } from './datasets'
export type AgentTool = { name: string; description?: string; source: ToolSource; approval?: boolean
  server_id?: string; tool?: string; url_binding?: UrlBinding; parameters?: Schema; function?: string; knowledge_base_id?: string; top_k?: number
  method?: string; url?: string; body?: string
  workflow_id?: string; inputs?: string[]; outputs?: string[]
  dataset_id?: string; fields?: string[]; filter_ops?: Record<string, string[]>; limit?: number
  operations?: DatasetAgentOperation[]; write_fields?: string[]; key?: string }
export type BuiltinTool = { name: string; doc?: string; parameters?: Schema | null }

export const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
export const PARAM_TYPES = ['string', 'number', 'integer', 'boolean']

/** A provider-safe tool name (letters, digits, _ and -, at most 64), unique among `taken`. */
export function toolName(raw: string, taken: string[]): string {
  const base = (raw.replace(/[^A-Za-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '') || 'tool').slice(0, 60)
  let name = base; let i = 2
  while (taken.includes(name)) name = `${base}_${i++}`
  return name
}

/** A new tool of `source`, named so it does not clash with the node's other tools. */
export function newTool(source: ToolSource, taken: string[]): AgentTool {
  const name = toolName({ mcp: 'mcp_tool', http: 'http_request', builtin: 'function', knowledge: 'search_knowledge', workflow: 'workflow', dataset: 'find_dataset_rows' }[source], taken)
  if (source === 'http') return { name, source, description: '', method: 'GET', url: '', body: '', parameters: { type: 'object', properties: {} } }
  if (source === 'knowledge') return { name, source, description: '', knowledge_base_id: '', top_k: 4 }
  if (source === 'dataset') return { name, source, description: '', dataset_id: '', fields: [], filter_ops: {}, limit: 10 }
  if (source === 'workflow') return { name, source, description: '', workflow_id: '', inputs: [], outputs: [] }
  return { name, source, description: '' }
}

/** An Agent node's tool names, for the Tests panel's "tool called" check. */
export const toolNames = (data: unknown): string[] => (((data as { tools?: AgentTool[] })?.tools) ?? []).map(t => t.name).filter(Boolean)
/** Whether an Agent node asks a person before a tool call: test cases answer it like a Human node. */
export const needsApproval = (data: unknown): boolean => (((data as { tools?: AgentTool[] })?.tools) ?? []).some(t => t.approval)

/** The fields a workflow tool sends and gets back when its workflow is picked: `message` in and `answer` out when the
 *  workflow has them (the usual chat shape), else its first field in and its last field out. */
export function defaultFields(fields: string[]): { inputs: string[]; outputs: string[] } {
  if (!fields.length) return { inputs: [], outputs: [] }
  const inputs = [fields.includes('message') ? 'message' : fields[0]]
  const out = fields.includes('answer') ? 'answer' : fields[fields.length - 1]
  return { inputs, outputs: out === inputs[0] && fields.length > 1 ? [fields.find(f => f !== inputs[0])!] : [out] }
}
