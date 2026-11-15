import { previewLayout, type Template } from '@/lib/templates'

/** Static thumbnail of a template graph: node colours come from the --node-* theme vars (strict shadcn). */
const FILL: Record<string, string> = {
  start: 'fill-node-start', end: 'fill-node-end', llm: 'fill-node-llm', tool: 'fill-node-tool', condition: 'fill-node-condition', code: 'fill-node-code',
  human: 'fill-node-human', join: 'fill-node-join', mcp: 'fill-node-mcp', retriever: 'fill-node-retriever', dataset: 'fill-node-retriever', subgraph: 'fill-node-subgraph', foreach: 'fill-node-foreach', decision: 'fill-node-decision', email: 'fill-node-email',
}

export function TemplatePreview({ tpl, w = 240, h = 96 }: { tpl: Pick<Template, 'nodes' | 'edges'>; w?: number; h?: number }) {
  const p = previewLayout(tpl.nodes, w, h)
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-24 rounded-md bg-muted/50" aria-hidden="true" data-testid="tpl-preview">
      {tpl.edges.map((e, i) => p[e.source] && p[e.target] &&
        <line key={i} x1={p[e.source].x} y1={p[e.source].y} x2={p[e.target].x} y2={p[e.target].y} className="stroke-muted-foreground/50" strokeWidth={1.5} />)}
      {tpl.nodes.map(n => <rect key={n.id} x={p[n.id].x - 9} y={p[n.id].y - 6} width={18} height={12} rx={3} className={`${FILL[n.type] ?? 'fill-muted-foreground'} stroke-background`} strokeWidth={1} />)}
    </svg>
  )
}
