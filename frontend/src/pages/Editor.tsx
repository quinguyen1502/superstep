import { useState } from 'react'
import { ReactFlowProvider } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { EditorLayout, type MobileView } from '@/components/editor-layout'
import { EditorSkeleton } from '@/components/editor/editor-skeleton'
import { EditorHeader } from '@/components/editor/editor-header'
import { EditorPalette } from '@/components/editor/editor-palette'
import { EditorCanvas } from '@/components/editor/editor-canvas'
import { EditorConfig } from '@/components/editor/editor-config'
import { EditorRunPanel } from '@/components/editor/editor-run-panel'
import { ChatSidePanel } from '@/components/chat/chat-side-panel'
import { StudioContext } from '@/components/editor/studio-context'
import { useStudio } from '@/components/editor/use-studio'
import { useIsMobile, useViewportWidth } from '@/lib/use-viewport-width'
import { CONFIG_COLLAPSE_BELOW, chatStore } from '@/lib/panel-sizes'

/** Workflow editor page. State and actions live in `useStudio`; the header and panels are in components/editor (TASK-0040). */
export function EditorPage() { return <ReactFlowProvider><Studio /></ReactFlowProvider> }

function Studio() {
  const { t } = useTranslation()
  const studio = useStudio(); const { id, wid, loadErr } = studio
  // narrow screens (TASK-0085): Config folds away while nothing is selected, so the canvas keeps its room beside the chat
  const vw = useViewportWidth()
  const narrow = vw - (studio.chatOpen ? chatStore.read().width : 0) < CONFIG_COLLAPSE_BELOW
  // phones (TASK-0121): one pane at a time; a run shows the Run pane, opening the chat shows the chat
  const mobile = useIsMobile(); const [view, setView] = useState<MobileView>('canvas')
  const { running, chatOpen, addCentered } = studio
  const [seen, setSeen] = useState({ running, chatOpen })
  if (seen.running !== running || seen.chatOpen !== chatOpen) {
    setSeen({ running, chatOpen })
    if (chatOpen !== seen.chatOpen) setView(chatOpen ? 'chat' : view === 'chat' ? 'canvas' : view)
    if (running && !seen.running) setView('run')
  }
  // a tap on a palette card adds the node in the middle of the canvas, once the canvas is showing again
  const addFromPalette = (type: string) => { setView('canvas'); requestAnimationFrame(() => addCentered(type)) }
  if (!wid && id && !loadErr) return <EditorSkeleton />

  if (loadErr) return <div className="min-h-screen flex items-center justify-center bg-muted/40 p-4 text-foreground">
    <div className="max-w-sm text-center space-y-3 rounded-xl border bg-card p-8 shadow-sm" id="editor-not-found">
      <div className="mx-auto w-fit rounded-full bg-muted p-3 text-muted-foreground"><ArrowLeft className="size-5" /></div>
      <h1 className="text-lg font-semibold">{t(loadErr.status === 404 ? 'editor.notFoundTitle' : 'editor.openFailedTitle')}</h1>
      <p className="text-sm text-muted-foreground">{loadErr.status === 404 ? t('editor.notFoundBody') : loadErr.msg}</p>
      <Button asChild><Link to="/workflows" id="back-to-list">{t('editor.backToList')}</Link></Button>
    </div>
  </div>

  return <StudioContext.Provider value={studio}>
    <EditorLayout className="text-foreground text-sm" header={<EditorHeader />} left={<EditorPalette onAdd={mobile ? addFromPalette : undefined} />} canvas={<EditorCanvas />}
      right={<EditorConfig />} bottom={<EditorRunPanel />} rightCollapsed={narrow && !studio.selNode && !studio.selEdge}
      mobile={mobile ? { view, onView: setView, selected: !!(studio.selNode || studio.selEdge) } : undefined}
      chat={studio.chatOpen && wid ? <ChatSidePanel wid={wid} canConfigure={studio.access === 'owner'} dirty={studio.edit && studio.isDirty()} onClose={() => studio.setChatOpen(false)} /> : undefined} />
  </StudioContext.Provider>
}
