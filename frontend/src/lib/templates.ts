/** Template library: API types, the portable file helpers and the mini-preview geometry. */
export type TplNode = { id: string; type: string; position: { x: number; y: number } }
export type Template = { id: string; name: string; description: string; scope: 'builtin' | 'user' | 'org'; mine: boolean; deletable?: boolean
  tests: number  // test cases a workflow made from it gets (built-in templates, )
  nodes: TplNode[]; edges: { source: string; target: string }[] }
export const TEMPLATE_FORMAT = 'superstep/template'

/** Fit node positions into a w×h box (keeping aspect, with padding); returns centre points per node id. */
export function previewLayout(nodes: TplNode[], w = 240, h = 96, pad = 12): Record<string, { x: number; y: number }> {
  if (!nodes.length) return {}
  const xs = nodes.map(n => n.position.x), ys = nodes.map(n => n.position.y)
  const minX = Math.min(...xs), minY = Math.min(...ys), spanX = Math.max(...xs) - minX, spanY = Math.max(...ys) - minY
  const s = Math.min((w - 2 * pad) / (spanX || 1), (h - 2 * pad) / (spanY || 1))
  const ox = (w - spanX * s) / 2, oy = (h - spanY * s) / 2
  return Object.fromEntries(nodes.map(n => [n.id, { x: ox + (n.position.x - minX) * s, y: oy + (n.position.y - minY) * s }]))
}

/** Read a picked file as JSON; throws a readable message for non-JSON. Validation happens server-side. */
export async function readTemplateFile(f: File): Promise<unknown> {
  const text = await f.text()
  try { return JSON.parse(text) } catch { throw new Error('invalid-json') }
}

export const fileName = (name: string) => `${name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'template'}.template.json`

export function download(name: string, payload: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }))
  const a = document.createElement('a'); a.href = url; a.download = fileName(name); a.click(); URL.revokeObjectURL(url)
}
