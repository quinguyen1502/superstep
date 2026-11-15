/** `{{state.field}}` references in node templates.
 * The pattern matches backend `engine/templating.py` VAR_RE: `{{ state.field[.key|.0]... [| filter[(arg)]]... }}`. */
const NAME = '[A-Za-z_][A-Za-z0-9_]*'
const ARG = String.raw`"[^"]*"|'[^']*'|-?\d+`
const FILTER = String.raw`\|\s*${NAME}\s*(?:\(\s*(?:${ARG})\s*\))?\s*`
const VAR = String.raw`\{\{\s*state\.(${NAME})((?:\.(?:${NAME}|\d+))*)\s*((?:${FILTER})*)\}\}`
const ONE_FILTER = String.raw`\|\s*(${NAME})\s*(?:\(\s*(${ARG})\s*\))?\s*`

/** A fresh global regex: group 1 is the field, group 2 the `.a.0` path, group 3 the filter chain. */
export const stateRefRe = () => new RegExp(VAR, 'g')

export const stateRef = (field: string) => `{{state.${field}}}`

/** Filters the backend knows, with the argument each one needs. */
export const FILTERS = { upper: 'none', lower: 'none', trim: 'none', json: 'none', length: 'none', first: 'none', last: 'none', default: 'text', join: 'text', truncate: 'number' } as const
export type FilterName = keyof typeof FILTERS
export type Ref = { field: string; path: string[]; filters: { name: string; arg?: string }[] }

export function parseRef(m: RegExpMatchArray): Ref {
  return { field: m[1], path: m[2].split('.').filter(Boolean),
    filters: [...(m[3] || '').matchAll(new RegExp(ONE_FILTER, 'g'))].map(f => ({ name: f[1], ...(f[2] !== undefined ? { arg: f[2] } : {}) })) }
}

/** The first filter that the backend would refuse (unknown name or wrong argument), if any. */
export function badFilter(ref: Ref): string | undefined {
  return ref.filters.find(f => {
    const kind = FILTERS[f.name as FilterName]
    if (!kind) return true
    if (kind === 'none') return f.arg !== undefined
    return f.arg === undefined || (kind === 'number') !== /^-?\d+$/.test(f.arg)
  })?.name
}

/** What a tag shows: `order.items.0 | upper`. */
export const refLabel = (ref: Ref) => [[ref.field, ...ref.path].join('.'), ...ref.filters.map(f => f.arg === undefined ? f.name : `${f.name}(${f.arg})`)].join(' | ')

/** A reference being typed at the end of `before`: where its `{{` starts and where the field name starts. */
export function openRef(before: string): { start: number; name: number } | null {
  const m = /\{\{\s*(?:state\.)?([A-Za-z0-9_]*)$/.exec(before)
  return m ? { start: m.index, name: before.length - m[1].length } : null
}

/** A filter name being typed after `|` inside a reference: where the name starts. */
export function openFilter(before: string): { name: number } | null {
  const m = new RegExp(String.raw`\{\{\s*state\.${NAME}(?:\.(?:${NAME}|\d+))*\s*(?:${FILTER})*\|\s*([A-Za-z_]*)$`).exec(before)
  return m ? { name: before.length - m[1].length } : null
}

/** How many characters of `after` close a reference being completed (`}}`, with spaces before it). */
export function closeLen(after: string): number {
  return /^\s*\}\}/.exec(after)?.[0].length ?? 0
}
