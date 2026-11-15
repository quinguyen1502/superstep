/** Editor panel sizes in px. One localStorage key in this browser; never part of the workflow,
 * so another author does not inherit them. Missing, corrupt or too-small values fall back to the defaults / minimums. */
export type PanelSizes = { left: number; right: number; bottom: number }

export const PANEL_KEY = 'lgs.editorPanels'
export const PANEL_DEFAULT: PanelSizes = { left: 250, right: 320, bottom: 300 }
export const PANEL_MIN: PanelSizes = { left: 180, right: 260, bottom: 140 }
export const CANVAS_MIN = { width: 280, height: 160 }

const KEYS = Object.keys(PANEL_DEFAULT) as (keyof PanelSizes)[]

export function parseSizes(raw: string | null): PanelSizes {
  let v: Record<string, unknown> | null = null
  try { v = JSON.parse(raw ?? 'null') } catch { /* corrupt value: defaults */ }
  const pick = (k: keyof PanelSizes) => { const n = v?.[k]; return typeof n === 'number' && Number.isFinite(n) ? Math.max(PANEL_MIN[k], Math.round(n)) : PANEL_DEFAULT[k] }
  return Object.fromEntries(KEYS.map(k => [k, pick(k)])) as PanelSizes
}

export const panelStore = {
  read: (): PanelSizes => { try { return parseSizes(localStorage.getItem(PANEL_KEY)) } catch { return { ...PANEL_DEFAULT } } },
  write: (s: PanelSizes) => { try { localStorage.setItem(PANEL_KEY, JSON.stringify(s)) } catch { /* storage disabled: sizes last for this page */ } },
}

/** The Chat side panel: open or not, and its width in px (340–760). Same rules as the panel sizes:
 * one key in this browser, corrupt or out-of-range values fall back to the default / the nearest bound. */
export type ChatPanelState = { open: boolean; width: number }
export const CHAT_KEY = 'lgs.chatPanel'
export const CHAT_WIDTH = { min: 340, max: 760, default: 420 }
/** Below this editor width (viewport minus an open chat) Config collapses unless a node or edge is selected. */
export const CONFIG_COLLAPSE_BELOW = 1100

export function parseChat(raw: string | null): ChatPanelState {
  let v: Record<string, unknown> | null = null
  try { v = JSON.parse(raw ?? 'null') } catch { /* corrupt value: defaults */ }
  const w = v?.width
  return { open: v?.open === true,
    width: typeof w === 'number' && Number.isFinite(w) ? Math.min(CHAT_WIDTH.max, Math.max(CHAT_WIDTH.min, Math.round(w))) : CHAT_WIDTH.default }
}

export const chatStore = {
  read: (): ChatPanelState => { try { return parseChat(localStorage.getItem(CHAT_KEY)) } catch { return { open: false, width: CHAT_WIDTH.default } } },
  write: (patch: Partial<ChatPanelState>) => { try { localStorage.setItem(CHAT_KEY, JSON.stringify({ ...chatStore.read(), ...patch })) } catch { /* storage disabled */ } },
}
