import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Blocks, MessagesSquare, Play, SlidersHorizontal, Workflow, type LucideIcon } from 'lucide-react'
import { usePanelRef, type PanelSize } from 'react-resizable-panels'
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CANVAS_MIN, CHAT_WIDTH, PANEL_MIN, chatStore, panelStore, type PanelSizes } from '@/lib/panel-sizes'
import { cn } from '@/lib/utils'

/** Editor chrome (TASK-0038, REQ-0026): the 56px header, then palette | canvas | config over the run panel. The three
 * borders drag; the canvas takes what is left. Sizes are read once per mount and saved after a user drag only, so the
 * loading skeleton and the next workflow open with the same sizes.
 * Chat (TASK-0085) is a full-height column right of all of it, 340–760px, its width saved the same way. Config stays
 * beside the chat; `rightCollapsed` folds it away (narrow screens with nothing selected) and drags back open.
 * With `mobile` set (phones, TASK-0121) the panes stack instead and a bottom tab bar switches between them. */
export function EditorLayout({ header, left, canvas, right, bottom, chat, rightCollapsed = false, className, busy, mobile }: {
  header: ReactNode; left: ReactNode; canvas: ReactNode; right: ReactNode; bottom: ReactNode; chat?: ReactNode; rightCollapsed?: boolean; className?: string; busy?: boolean
  mobile?: MobileViews
}) {
  if (mobile) return <MobileEditorLayout {...{ header, left, canvas, right, bottom, chat, className, busy, ...mobile }} />
  return <DesktopEditorLayout {...{ header, left, canvas, right, bottom, chat, rightCollapsed, className, busy }} />
}

export type MobileView = 'canvas' | 'nodes' | 'config' | 'run' | 'chat'
/** Phone layout: which pane shows, and a dot on Config while a node or edge is selected. */
export type MobileViews = { view: MobileView; onView: (v: MobileView) => void; selected?: boolean }

/** Phones (TASK-0121): one pane at a time under the header, picked from a tab bar at the bottom. Every pane stays
 * mounted (only hidden), so the canvas keeps its viewport and the run panel its scroll when you switch. */
function MobileEditorLayout({ header, left, canvas, right, bottom, chat, className, busy, view, onView, selected }: {
  header: ReactNode; left: ReactNode; canvas: ReactNode; right: ReactNode; bottom: ReactNode; chat?: ReactNode; className?: string; busy?: boolean
} & MobileViews) {
  const { t } = useTranslation()
  const panes: [MobileView, LucideIcon, string, ReactNode][] = [
    ['canvas', Workflow, t('editor.mobileNav.canvas'), canvas], ['nodes', Blocks, t('editor.mobileNav.nodes'), left],
    ['config', SlidersHorizontal, t('editor.config'), right], ['run', Play, t('editor.tabRun'), bottom],
    ...(chat ? [['chat', MessagesSquare, t('chat.tab'), chat] as [MobileView, LucideIcon, string, ReactNode]] : [])]
  const current = view === 'chat' && !chat ? 'canvas' : view
  return <div className={cn('h-dvh flex flex-col bg-background', className)} aria-busy={busy || undefined}>
    {header}
    <Tabs value={current} onValueChange={v => onView(v as MobileView)} className="min-h-0 flex-1 gap-0" id="mobile-editor">
      {panes.map(([id, , , node]) => <TabsContent key={id} value={id} forceMount className="min-h-0 data-[state=inactive]:hidden" id={`mobile-pane-${id}`}>{node}</TabsContent>)}
      <div className="flex h-14 shrink-0 items-center border-t px-2">
        <TabsList className="w-full" aria-label={t('editor.mobileNav.label')}>
          {panes.map(([id, I, label]) => <TabsTrigger key={id} value={id} id={`mobile-tab-${id}`} className="min-w-0">
            {/* five tabs do not fit a phone with labels: the others keep their icon, the label stays for screen readers */}
            <I /><span className={cn('truncate', panes.length > 4 && id !== current && 'max-sm:sr-only')}>{label}</span>
            {id === 'config' && selected && <span className="absolute top-1 right-1 size-1.5 rounded-full bg-primary" data-testid="mobile-config-dot" />}
          </TabsTrigger>)}
        </TabsList>
      </div>
    </Tabs>
  </div>
}

function DesktopEditorLayout({ header, left, canvas, right, bottom, chat, rightCollapsed = false, className, busy }: {
  header: ReactNode; left: ReactNode; canvas: ReactNode; right: ReactNode; bottom: ReactNode; chat?: ReactNode; rightCollapsed?: boolean; className?: string; busy?: boolean
}) {
  const { t } = useTranslation()
  const [init] = useState(panelStore.read)
  const [chatWidth] = useState(() => chatStore.read().width)
  const px = useRef<PanelSizes>({ ...init })
  const track = (k: keyof PanelSizes) => (s: PanelSize) => { if (s.inPixels > 0) px.current[k] = Math.round(s.inPixels) }
  const save = (_: unknown, meta: { isUserInteraction: boolean }) => { if (meta.isUserInteraction) panelStore.write(px.current) }
  const chatPx = useRef(chatWidth)
  const saveChat = (_: unknown, meta: { isUserInteraction: boolean }) => { if (meta.isUserInteraction) chatStore.write({ width: chatPx.current }) }
  const rightRef = usePanelRef()
  // after the chat column comes or goes the outer group lays out again, so apply the fold on the next frame
  const hasChat = !!chat
  useEffect(() => {
    const f = requestAnimationFrame(() => { const p = rightRef.current; if (!p) return
      if (rightCollapsed) { if (!p.isCollapsed()) p.collapse() } else if (p.isCollapsed()) p.expand() })
    return () => cancelAnimationFrame(f)
  }, [rightCollapsed, hasChat, rightRef])
  const side = { groupResizeBehavior: 'preserve-pixel-size', className: 'min-h-0' } as const
  return <div className={cn('h-screen flex flex-col bg-background', className)} aria-busy={busy || undefined}>
    {header}
    <ResizablePanelGroup orientation="horizontal" className="min-h-0 flex-1" onLayoutChanged={saveChat}>
      <ResizablePanel id="panel-editor" minSize={CANVAS_MIN.width + PANEL_MIN.left} className="min-h-0">
        <ResizablePanelGroup orientation="vertical" className="h-full min-h-0" onLayoutChanged={save}>
          <ResizablePanel id="panel-main" minSize={CANVAS_MIN.height} className="min-h-0">
            <ResizablePanelGroup orientation="horizontal" onLayoutChanged={save}>
              <ResizablePanel id="panel-left" defaultSize={init.left} minSize={PANEL_MIN.left} onResize={track('left')} {...side}>{left}</ResizablePanel>
              <ResizableHandle id="resize-left" aria-label={t('editor.resizePalette')} disableDoubleClick />
              <ResizablePanel id="panel-canvas" minSize={CANVAS_MIN.width} className="min-h-0">{canvas}</ResizablePanel>
              <ResizableHandle id="resize-right" aria-label={t('editor.resizeConfig')} disableDoubleClick />
              <ResizablePanel id="panel-right" panelRef={rightRef} defaultSize={rightCollapsed ? 0 : init.right} minSize={PANEL_MIN.right} collapsible collapsedSize={0}
                onResize={track('right')} {...side}>{right}</ResizablePanel>
            </ResizablePanelGroup>
          </ResizablePanel>
          <ResizableHandle id="resize-bottom" aria-label={t('editor.resizeRun')} disableDoubleClick />
          <ResizablePanel id="panel-bottom" defaultSize={init.bottom} minSize={PANEL_MIN.bottom} onResize={track('bottom')} {...side}>{bottom}</ResizablePanel>
        </ResizablePanelGroup>
      </ResizablePanel>
      {chat && <><ResizableHandle id="resize-chat" withHandle aria-label={t('chat.resize')} disableDoubleClick />
        <ResizablePanel id="panel-chat" defaultSize={chatWidth} minSize={CHAT_WIDTH.min} maxSize={CHAT_WIDTH.max}
          onResize={s => { if (s.inPixels > 0) chatPx.current = Math.round(s.inPixels) }} {...side}>{chat}</ResizablePanel></>}
    </ResizablePanelGroup>
  </div>
}
