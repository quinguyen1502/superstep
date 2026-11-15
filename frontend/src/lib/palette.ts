/** Command palette: pages contribute commands while mounted (the editor adds its actions, node
 * types and nodes); the palette adds navigation and workflows. Small external store, no context provider needed. */
import { useSyncExternalStore } from 'react'
import type { LucideIcon } from 'lucide-react'

export type CommandGroupId = 'actions' | 'add' | 'nodes' | 'workflows' | 'navigation'
export type PaletteCommand = {
  id: string; group: CommandGroupId; label: string; hint?: string
  keywords?: string[]; shortcut?: string /* registry id: its keys are shown */; icon?: LucideIcon; disabled?: boolean
  menu?: MenuSection /* also listed in the editor's ⋯ menu */; destructive?: boolean; elementId?: string /* stable DOM id for the menu item */
  run: () => void
}
export type MenuSection = 'arrange' | 'workflow' | 'help' | 'danger'
export const MENU_ORDER: MenuSection[] = ['arrange', 'workflow', 'help', 'danger']
export const GROUP_ORDER: CommandGroupId[] = ['actions', 'add', 'nodes', 'workflows', 'navigation']

const sources = new Map<string, PaletteCommand[]>(); const subs = new Set<() => void>()
let snapshot: PaletteCommand[] = []
const emit = () => { snapshot = [...sources.values()].flat(); subs.forEach(f => f()) }

/** Contribute commands under `key` (replacing that key's previous list). Returns the unregister function. */
export function registerCommands(key: string, cmds: PaletteCommand[]): () => void {
  sources.set(key, cmds); emit()
  return () => { if (sources.get(key) === cmds) { sources.delete(key); emit() } }
}
export const subscribe = (f: () => void) => { subs.add(f); return () => { subs.delete(f) } }
export const getCommands = () => snapshot
export function usePaletteCommands(): PaletteCommand[] { return useSyncExternalStore(subscribe, getCommands, getCommands) }

/** Group commands in display order, dropping empty groups (unique ids, first wins). */
export function grouped(cmds: PaletteCommand[]): [CommandGroupId, PaletteCommand[]][] {
  const seen = new Set<string>(); const by = new Map<CommandGroupId, PaletteCommand[]>()
  for (const c of cmds) { if (seen.has(c.id)) continue; seen.add(c.id); (by.get(c.group) ?? by.set(c.group, []).get(c.group)!).push(c) }
  return GROUP_ORDER.filter(g => by.get(g)?.length).map(g => [g, by.get(g)!])
}

/** cmdk search value: label + hint + keywords, so e.g. "kb" finds "Retriever (knowledge base)". */
export const searchValue = (c: PaletteCommand) => [c.label, c.hint, ...(c.keywords ?? []), c.id].filter(Boolean).join(' ')

/** Where a node added from the palette goes: the view centre, nudged until it doesn't sit on an existing node. */
export function freeSpot(center: { x: number; y: number }, taken: { x: number; y: number }[], step = 40, size = { w: 200, h: 70 }) {
  const p = { x: Math.round(center.x - size.w / 2), y: Math.round(center.y - size.h / 2) }
  for (let i = 0; i < 50 && taken.some(t => Math.abs(t.x - p.x) < size.w * 0.6 && Math.abs(t.y - p.y) < size.h * 0.8); i++) { p.x += step; p.y += step }
  return p
}

/** The editor's ⋯ menu: the commands flagged with `menu`, in section order (empty sections dropped). */
export function menuSections(cmds: PaletteCommand[]): [MenuSection, PaletteCommand[]][] {
  return MENU_ORDER.map(m => [m, cmds.filter(c => c.menu === m)] as [MenuSection, PaletteCommand[]]).filter(([, v]) => v.length)
}

/** Ask the app-wide palette to open (from a menu item or button). */
const openers = new Set<() => void>()
export const onPaletteRequest = (f: () => void) => { openers.add(f); return () => { openers.delete(f) } }
export const openPalette = () => openers.forEach(f => f())
