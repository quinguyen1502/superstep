import { ReactFlow, Background, Controls, ControlButton, MiniMap } from '@xyflow/react'
import { Plus, Trash2, StickyNote } from 'lucide-react'
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuSeparator, ContextMenuTrigger } from '@/components/ui/context-menu'
import { copySelection } from '@/lib/clipboard'
import { useTranslation } from 'react-i18next'
import { InsertMenu, NodeMenu } from './parts'
import { useStudioCtx } from './studio-context'
import { CanvasLockIcon } from './canvas-nodes'
import { CanvasEdit } from './canvas-edit'
import { nodeTypes } from './node-types'
import { Tip } from '@/components/tip'
import { removable } from '@/lib/graph-ops'
import { useIsMobile } from '@/lib/use-viewport-width'

/** Canvas with its context menu (TASK-0040). */
export function EditorCanvas() {
  const { t } = useTranslation()
  const mobile = useIsMobile()  // phones (TASK-0121): zoom out further so a whole workflow fits the narrow screen
  const { nodes, setNodes, onNodesChange, edges, setEdges, onEdgesChange, setSel, source, edit, dark, rf, removeIds, clipNote, copyIds, insert, editable, insertAround, addNode, addNote, ctx, setCtx, nodesView, onNodeClick, onConnect, onDrop, canvasLock, setCanvasLock } = useStudioCtx()
  return <ContextMenu>
    <ContextMenuTrigger asChild>
    <main className="h-full min-h-0" onDrop={onDrop} onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }}>
      {clipNote && <div role="status" id="clip-notice" className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 rounded-md border bg-popover text-popover-foreground shadow-md px-3 py-1.5 text-sm">{clipNote}</div>}
      <CanvasEdit.Provider value={editable}>
      <ReactFlow nodes={nodesView} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
        colorMode={dark ? 'dark' : 'light'} onConnect={edit && !canvasLock ? onConnect : undefined} nodesConnectable={edit && !canvasLock} nodesDraggable={edit && !canvasLock} edgesReconnectable={edit && !canvasLock} elementsSelectable
        onNodeClick={(_, n) => onNodeClick(n.id)}
        onNodeContextMenu={(e, n) => {
          if (!edit || source) { e.preventDefault(); e.stopPropagation(); return }
          setCtx({ kind: 'node', id: n.id })
          setNodes(ns => ns.map(x => ({ ...x, selected: x.id === n.id })))
          setEdges(es => es.some(ed => ed.selected) ? es.map(ed => ({ ...ed, selected: false })) : es)
          onNodeClick(n.id)
        }}
        onEdgeClick={(_, e) => setSel({ kind: 'edge', id: e.id })}
        onEdgeContextMenu={(e, ed) => { if (!edit || source) { e.preventDefault(); e.stopPropagation(); return } setCtx({ kind: 'edge', id: ed.id }); setSel({ kind: 'edge', id: ed.id }) }}
        onPaneContextMenu={e => { if (!editable) { e.preventDefault(); e.stopPropagation(); return } setCtx({ kind: 'pane', at: rf.screenToFlowPosition({ x: e.clientX, y: e.clientY }) }) }}
        onPaneClick={() => setSel(null)} deleteKeyCode={null} fitView minZoom={mobile ? 0.2 : undefined}>
        <Background /><Controls showInteractive={false}>
          <Tip tip={t(canvasLock ? 'editor.unlockCanvas' : 'editor.lockCanvas')}><ControlButton onClick={() => setCanvasLock(v => !v)} aria-label={t(canvasLock ? 'editor.unlockCanvas' : 'editor.lockCanvas')}>
            <CanvasLockIcon locked={canvasLock} />
          </ControlButton></Tip>
        </Controls><MiniMap pannable zoomable className="[&>svg]:h-20 [&>svg]:w-28 max-md:hidden" />
      </ReactFlow>
      </CanvasEdit.Provider>
    </main>
    </ContextMenuTrigger>
    <ContextMenuContent>
      {ctx?.kind === 'pane' && <>
        <InsertMenu id="pane" label={t('editor.addNode')} icon={Plus} onPick={type => addNode(type, ctx.at, true)} />
        <ContextMenuItem id="add-note" onSelect={() => addNote(ctx.at)}><StickyNote />{t('editor.addNote')}</ContextMenuItem>
      </>}
      {ctx?.kind === 'node' && <NodeMenu id={ctx.id} type={nodes.find(n => n.id === ctx.id)?.type} edges={edges} canDelete={removable(nodes, [ctx.id]).size > 0} insert={insertAround}
        onCopy={() => copyIds([ctx.id])}
        onCut={() => copyIds([ctx.id], true)}
        onDuplicate={() => { const c = copySelection(nodes, edges, [ctx.id]); if (c) insert(c, 1) }} onDelete={() => removeIds([ctx.id])} />}
      {ctx?.kind === 'edge' && <>
        <InsertMenu id="edge" label={t('editor.insertHere')} icon={Plus} onPick={type => ctx && insertAround(type, { dir: 'edge', edgeId: ctx.id })} />
        <ContextMenuSeparator />
        <ContextMenuItem id="delete-edge" variant="destructive" onSelect={() => ctx && removeIds([], [ctx.id])}><Trash2 />{t('editor.deleteEdge')}</ContextMenuItem>
      </>}
    </ContextMenuContent>
    </ContextMenu>
}
