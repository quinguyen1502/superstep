/** Contextual handbook links (TASK-0260, DEC-0086 option A): fixed published handbook, `/vi/` for Vietnamese. */
export const HANDBOOK_URL = 'https://quinguyen1502.github.io/superstep/'

/** `page` is a handbook path such as `operate/channels` (no `.md`); `anchor` a heading id. */
export function handbookUrl(page: string, lang?: string | null, anchor?: string): string {
  const base = HANDBOOK_URL + (lang?.toLowerCase().startsWith('vi') ? 'vi/' : '')
  const path = page.replace(/^\/+|\/+$/g, '').replace(/\.md$/, '')
  return `${base}${path ? `${path}/` : ''}${anchor ? `#${anchor}` : ''}`
}
