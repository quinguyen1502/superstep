// Expected Vietnamese text for the specs. UI strings come from the app's own catalog (src/locales/vi.json), so an
// assertion checks the real translation; Vietnamese test inputs (chat messages, names, prompts) live in
// fixtures/inputs.vi.json. Keys are dotted paths; {{name}} placeholders are filled from `vars`.
import vi from '../src/locales/vi.json' with { type: 'json' }
import inputs from './fixtures/inputs.vi.json' with { type: 'json' }
import server from '../../backend/app/locales/vi.json' with { type: 'json' }

type Tree = { [key: string]: string | Tree }

function lookup(tree: Tree, key: string, vars: Record<string, string | number>, source: string): string {
  const value = key.split('.').reduce<string | Tree | undefined>((node, part) => (node && typeof node === 'object' ? node[part] : undefined), tree)
  if (typeof value !== 'string') throw new Error(`${source} has no string at ${key}`)
  return value.replace(/\{\{\s*(\w+)\s*\}\}/g, (match, name: string) => (name in vars ? String(vars[name]) : match))
}

/** A string of the Vietnamese UI catalog. */
export const vt = (key: string, vars: Record<string, string | number> = {}) => lookup(vi as Tree, key, vars, 'src/locales/vi.json')

/** A Vietnamese test input (what a person types or names things in the Vietnamese specs). */
export const vin = (key: string, vars: Record<string, string | number> = {}) => lookup(inputs as Tree, key, vars, 'e2e/fixtures/inputs.vi.json')

/** A RegExp that matches `text` literally (for getByRole names and the like). */
export const literally = (text: string, flags = '') => new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), flags)

/** A RegExp that matches text starting with `text`. */
export const startsWith = (text: string) => new RegExp('^' + literally(text).source)

/**
 * The start of a catalog string, up to its first placeholder not given in `vars`: for UI text that ends with a
 * run-time value (a latency, a date, a version) that the spec cannot know.
 */
export function vtHead(key: string, vars: Record<string, string | number> = {}): string {
  const full = vt(key, vars), at = full.indexOf('{{')
  return (at < 0 ? full : full.slice(0, at)).replace(/[\s·:,(]+$/, '')
}

/** The Vietnamese test inputs as a tree (for specs that keep a whole block of names per language). */
export const viInputs = inputs

/** A string of the server's Vietnamese catalog (backend/app/locales/vi.json: chat messages, the offline mock). */
export const st = (key: string, vars: Record<string, string | number> = {}) =>
  lookup(server as unknown as Tree, key, {}, 'backend/app/locales/vi.json').replace(/\{(\w+)\}/g, (match, name: string) => (name in vars ? String(vars[name]) : match))
