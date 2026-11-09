/** Editor keyboard shortcuts: one registry used by the key handler, the cheat sheet and the
 * command palette. Combos are written platform-neutral: `mod` = ⌘ on macOS, Ctrl elsewhere. */
export type ShortcutGroup = 'general' | 'canvas' | 'history' | 'clipboard' | 'run'
export type Shortcut = { id: string; keys: string[]; group: ShortcutGroup; allowInInputs?: boolean }

export const SHORTCUTS: Shortcut[] = [
  { id: 'save', keys: ['mod+s'], group: 'general', allowInInputs: true },
  { id: 'palette', keys: ['mod+k'], group: 'general', allowInInputs: true },
  { id: 'cheatsheet', keys: ['?', 'mod+/'], group: 'general' },
  { id: 'escape', keys: ['escape'], group: 'general' },
  { id: 'run', keys: ['mod+enter'], group: 'run', allowInInputs: true },
  { id: 'stop', keys: ['mod+.'], group: 'run', allowInInputs: true },
  { id: 'undo', keys: ['mod+z'], group: 'history' },  // text fields keep their native undo
  { id: 'redo', keys: ['mod+shift+z', 'mod+y'], group: 'history' },
  { id: 'copy', keys: ['mod+c'], group: 'clipboard' },  // text fields and page text keep native copy
  { id: 'cut', keys: ['mod+x'], group: 'clipboard' },
  { id: 'paste', keys: ['mod+v'], group: 'clipboard' },
  { id: 'duplicate', keys: ['mod+d'], group: 'clipboard' },
  { id: 'delete', keys: ['delete', 'backspace'], group: 'canvas' },
  { id: 'selectAll', keys: ['mod+a'], group: 'canvas' },
  { id: 'fitView', keys: ['shift+1'], group: 'canvas' },
  { id: 'zoomIn', keys: ['mod+='], group: 'canvas' },
  { id: 'zoomOut', keys: ['mod+-'], group: 'canvas' },
  { id: 'layout', keys: ['shift+l'], group: 'canvas' },
  { id: 'chat', keys: ['shift+c'], group: 'general' },  // toggle the Chat side panel
]
export const GROUPS: ShortcutGroup[] = ['general', 'canvas', 'history', 'clipboard', 'run']

export const isMac = () => typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)

type KeyLike = Pick<KeyboardEvent, 'key' | 'code' | 'ctrlKey' | 'metaKey' | 'shiftKey' | 'altKey'>

/** Does the event match a combo such as `mod+shift+z`, `shift+1` or `?` (shifted characters match by `key`). */
export function matches(e: KeyLike, combo: string, mac = isMac()): boolean {
  const parts = combo.toLowerCase().split('+'); const key = parts.pop()!
  const want = { mod: parts.includes('mod'), shift: parts.includes('shift'), alt: parts.includes('alt') }
  const mod = mac ? e.metaKey : e.ctrlKey
  if (mod !== want.mod || e.altKey !== want.alt) return false
  if (mac ? e.ctrlKey : e.metaKey) return false
  const k = e.key.toLowerCase()
  if (key.length === 1 && !/[a-z0-9]/.test(key)) return k === key && (want.shift || !e.shiftKey || key === '?')  // punctuation: layout-aware
  if (e.shiftKey !== want.shift) return false
  if (/^[0-9]$/.test(key)) return e.code === `Digit${key}`  // shift+1 gives '!' as key
  return k === key || (key === 'enter' && k === 'enter')
}

/** Typing in a text field, select or code editor must not trigger canvas shortcuts. */
export function isTypingTarget(t: EventTarget | null): boolean {
  const el = t as HTMLElement | null
  if (!el || !el.tagName) return false
  if (el.isContentEditable) return true
  const tag = el.tagName.toLowerCase()
  if (tag === 'textarea' || tag === 'select') return true
  if (tag === 'input') return !['checkbox', 'radio', 'button', 'submit', 'range', 'color'].includes((el as HTMLInputElement).type)
  return el.getAttribute('role') === 'combobox' || el.getAttribute('role') === 'textbox'
}

/** Which registered shortcut (if any) an event triggers, honouring the typing rule. */
export function resolve(e: KeyLike & { target: EventTarget | null }, list = SHORTCUTS, mac = isMac()): Shortcut | undefined {
  const typing = isTypingTarget(e.target)
  return list.find(s => (!typing || s.allowInInputs) && s.keys.some(c => matches(e, c, mac)))
}

const NAMES: Record<string, [string, string]> = {  // [mac, other]
  mod: ['⌘', 'Ctrl'], shift: ['⇧', 'Shift'], alt: ['⌥', 'Alt'], enter: ['↵', 'Enter'], escape: ['Esc', 'Esc'],
  delete: ['⌦', 'Del'], backspace: ['⌫', 'Backspace'],
}
/** Key caps for one combo, e.g. `mod+shift+z` → ['Ctrl','Shift','Z'] or ['⌘','⇧','Z']. */
export function keyCaps(combo: string, mac = isMac()): string[] {
  return combo.split('+').map(p => NAMES[p]?.[mac ? 0 : 1] ?? (p.length === 1 ? p.toUpperCase() : p))
}
