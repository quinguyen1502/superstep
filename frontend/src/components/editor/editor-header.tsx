import { Fragment, useRef, useState } from 'react'
import { Redo2, Undo2, Play, Save, Loader2, GitFork, Check, MoreHorizontal, StepForward, FastForward, Crosshair, ArrowLeft, Square, MessagesSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuShortcut, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { JsonEditor } from '@/components/json-editor'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Link } from 'react-router-dom'
import { ApiTriggerDialog } from '@/components/api-trigger-dialog'
import { SchedulesDialog } from '@/components/schedules-dialog'
import { ChatTriggersDialog } from '@/components/chat-triggers-dialog'
import { ChatSettingsDialog } from '@/components/chat/chat-settings-dialog'
import { VersionsDialog } from '@/components/versions-dialog'
import { ShareDialog } from '@/components/share-dialog'
import { SaveTemplateDialog } from '@/components/save-template-dialog'
import { menuSections } from '@/lib/palette'
import { isMac, keyCaps, SHORTCUTS } from '@/lib/shortcuts'
import { api } from '@/lib/api'
import { useTranslation } from 'react-i18next'
import { LanguageSwitcher } from '@/components/language-switcher'
import { ThemeToggle } from '@/components/theme-toggle'
import { UserMenu } from '@/components/user-menu'
import { PendingBadge } from '@/components/pending-badge'
import { NotificationBell } from '@/components/notification-bell'
import { ShortcutCheatsheet } from '@/components/shortcut-cheatsheet'
import { Tip } from '@/components/tip'
import { useStudioCtx } from './studio-context'
import { LogoMark } from '@/components/logo'

const isMacPlatform = isMac()

/** Top bar: name, run controls, undo/redo, the ⋯ menu, dialogs, and account controls (TASK-0040). */
export function EditorHeader() {
  const { t } = useTranslation()
  const { input, name, setName, wid, setErrors, mode, source, setTab, running, access, ownerEmail, edit, canSave, hist, load, toJSON, save, run, cancelRun, layoutDir, cheat, setCheat, dlg, setDlg, delWf, isDirty, paletteCmds, trace, step, continueRun, selNode, d, runTo, chatOpen, setChatOpen, canChat } = useStudioCtx()
  // ⋯ tooltip: hidden while the menu is open and until the pointer leaves after closing it
  const [moreOpen, setMoreOpen] = useState(false); const [moreTip, setMoreTip] = useState(false); const moreTipBlock = useRef(false)
  // phones (TASK-0121): one row of back, name and icon-only actions; account controls stay on the workflow list
  return <header className="h-14 shrink-0 grid grid-cols-[minmax(min-content,1fr)_minmax(0,auto)_minmax(min-content,1fr)] items-center border-b px-4 max-md:flex max-md:gap-1 max-md:px-2">
      <div className="mr-3 flex min-w-0 items-center gap-2 max-md:mr-0">
        <Tip tip={t('editor.backToList')}><Button variant="ghost" size="icon" asChild><Link to="/workflows" id="back-btn"><ArrowLeft /></Link></Button></Tip>
        {/* the product name hides when its column is too narrow instead of running under the name field */}
        <div className="flex min-w-0 flex-1 items-center gap-2 font-semibold max-md:hidden" id="header-brand"><LogoMark />
          <div className="@container min-w-0 flex-1"><span className="hidden whitespace-nowrap @[8.5rem]:inline">Superstep</span></div></div>
      </div>
      <div className="flex min-w-0 items-center gap-2 max-md:flex-1 max-md:gap-1">
      <Input value={name} readOnly={!edit} onChange={e => setName(e.target.value)} className="w-72 min-w-28 max-md:w-auto max-md:min-w-0 max-md:flex-1" aria-label={t('editor.nameLabel')} />
      {edit && isDirty() && <Badge variant="outline" id="unsaved-badge" className="border-warning text-warning max-md:hidden">{t('history.unsaved')}</Badge>}
      {!canSave && <Tip tip={ownerEmail}><Badge variant="secondary" id="view-only" className="max-md:hidden">{t('editor.viewOnly')}</Badge></Tip>}
      {canSave && ownerEmail && <Tip tip={ownerEmail}><Badge variant="outline" id="shared-editor" className="max-md:hidden">{t('list.sharedBy', { email: ownerEmail })}</Badge></Tip>}
      <Tip tip={t('editor.saveTip')}><Button variant="outline" id="save-btn" onClick={save} disabled={!canSave}><Save /><span className="max-md:sr-only">{t('common.save')}</span></Button></Tip>
      <Tip tip={t('editor.runTip')}><Button id="run-btn" onClick={run} disabled={running}>{running ? <Loader2 className="animate-spin" /> : <Play />}<span className="max-md:sr-only">{t('editor.run')}</span></Button></Tip>
      {!source && <Tip tip={t('editor.stepTip')}><Button variant="outline" id="step-btn" className="max-md:hidden" onClick={step} disabled={running || trace.status === 'waiting'}>{running ? <Loader2 className="animate-spin" /> : <StepForward />}<span className="max-lg:sr-only">{t('editor.step')}</span></Button></Tip>}
      {!source && <Tip tip={selNode ? t('editor.runToTip', { node: d.label || selNode.id }) : t('editor.runToNeedNode')}><Button variant="outline" id="run-to-btn" className="max-md:hidden" onClick={runTo} disabled={running || trace.status === 'waiting' || !selNode || selNode.type === 'note'}><Crosshair /><span className="max-lg:sr-only">{t('editor.runTo')}</span></Button></Tip>}
      {!running && trace.paused && <Tip tip={t('editor.continueTip')}><Button variant="outline" id="continue-btn" onClick={continueRun}><FastForward /><span className="max-md:sr-only">{t('editor.continueRun')}</span></Button></Tip>}
      {canChat && <Tip tip={t('chat.openTip')}><Button variant={chatOpen ? 'secondary' : 'outline'} id="chat-open" aria-pressed={chatOpen} onClick={() => setChatOpen(!chatOpen)}><MessagesSquare /><span className="max-lg:sr-only">{t('chat.tab')}</span></Button></Tip>}
      {running && <Tip tip={t('editor.cancelTip')}><Button variant="outline" id="cancel-btn" onClick={cancelRun}><Square /><span className="max-md:sr-only">{t('common.cancel')}</span></Button></Tip>}
      {edit && <div className="flex items-center max-md:hidden" role="group" aria-label={t('history.group')}>
        <Tip tip={t('history.undoTip')}><Button variant="ghost" size="icon" id="undo-btn" aria-label={t('history.undo')} disabled={!hist.canUndo} onClick={hist.undo}><Undo2 /></Button></Tip>
        <Tip tip={t('history.redoTip')}><Button variant="ghost" size="icon" id="redo-btn" aria-label={t('history.redo')} disabled={!hist.canRedo} onClick={hist.redo}><Redo2 /></Button></Tip></div>}
      <DropdownMenu open={moreOpen} onOpenChange={o => { setMoreOpen(o); if (o) setMoreTip(false); else moreTipBlock.current = true }}>
        <Tooltip open={!moreOpen && moreTip} onOpenChange={o => { if (moreTipBlock.current || moreOpen) { setMoreTip(false); return } setMoreTip(o) }}>
          <TooltipTrigger asChild onPointerLeave={() => { moreTipBlock.current = false; setMoreTip(false) }}><DropdownMenuTrigger asChild><Button variant="ghost" size="icon" id="more-btn" aria-label={t('editor.more')}><MoreHorizontal /></Button></DropdownMenuTrigger></TooltipTrigger>
          <TooltipContent>{t('editor.moreTip')}</TooltipContent>
        </Tooltip>
        <DropdownMenuContent align="start" className="min-w-64" id="more-menu">
          {menuSections(paletteCmds).map(([sec, items], k) => <Fragment key={sec}>{k > 0 && <DropdownMenuSeparator />}
            {items.map(c => { const I = c.icon; const combo = c.shortcut ? SHORTCUTS.find(x => x.id === c.shortcut)?.keys[0] : undefined
              return <DropdownMenuItem key={c.id} id={c.elementId} data-testid="more-item" disabled={c.disabled} variant={c.destructive ? 'destructive' : 'default'} onSelect={() => c.run()}>
                {I && <I className={c.id === 'action:layout' && layoutDir === 'TB' ? 'rotate-90' : undefined} />}<span>{c.label}</span>
                {c.hint === '✓' && <Check className="ml-auto" />}
                {combo && <DropdownMenuShortcut>{keyCaps(combo).join(isMacPlatform ? '' : '+')}</DropdownMenuShortcut>}
              </DropdownMenuItem> })}</Fragment>)}
        </DropdownMenuContent>
      </DropdownMenu>
      </div>
      <div className="flex min-w-0 items-center justify-end gap-2">
      <ShortcutCheatsheet open={cheat} onOpenChange={setCheat} />
      {wid && <ShareDialog workflowId={wid} open={dlg === 'share'} onOpenChange={v => setDlg(v ? 'share' : null)} onTransferred={(o, f) => { setErrors(f.length ? [t('transfer.done', { email: o }), ...f.map(i => t('transfer.flaggedLine', { node: i.node, kind: t(`transfer.kinds.${i.kind}`), name: i.name ?? i.id }))] : [t('transfer.done', { email: o })]); setTab('input'); api(`/api/workflows/${wid}`).then(load).catch(() => {}) }} />}
      {edit && <SaveTemplateDialog wid={wid} defaultName={name} isDirty={isDirty} open={dlg === 'template'} onOpenChange={v => setDlg(v ? 'template' : null)} />}
      <VersionsDialog wid={wid} isDirty={isDirty} open={dlg === 'versions'} onOpenChange={v => setDlg(v ? 'versions' : null)} onRestored={wf => { load(wf); setErrors([]) }} />
      {access === 'owner' && <ApiTriggerDialog wid={wid} open={dlg === 'api'} onOpenChange={v => setDlg(v ? 'api' : null)} />}
      {access === 'owner' && <SchedulesDialog wid={wid} open={dlg === 'schedules'} onOpenChange={v => setDlg(v ? 'schedules' : null)} defaultInput={input} />}
      {access === 'owner' && !source && <ChatTriggersDialog wid={wid} open={dlg === 'chat'} onOpenChange={v => setDlg(v ? 'chat' : null)} />}
      {access === 'owner' && !source && <ChatSettingsDialog wid={wid} open={dlg === 'chatSettings'} onOpenChange={v => setDlg(v ? 'chatSettings' : null)} />}
      <Dialog open={dlg === 'json'} onOpenChange={v => setDlg(v ? 'json' : null)}>
        <DialogContent className="flex max-h-[85vh] w-full min-w-0 flex-col overflow-hidden sm:max-w-2xl">
          <DialogHeader className="shrink-0 pr-8"><DialogTitle>{t('editor.jsonTitle')}</DialogTitle><DialogDescription>{t('editor.jsonDesc')}</DialogDescription></DialogHeader>
          <JsonEditor readOnly value={JSON.stringify(toJSON(), null, 2)} className="h-[min(28rem,60vh)]" />
        </DialogContent>
      </Dialog>
      {delWf.dialog}
      {/* the right column is never narrower than its icons, so it cannot cover the centre actions; the info badges
          take what is left (TASK-0039) and hide whole when they do not fit, never as a clipped half badge */}
      <div className="@container flex min-w-0 flex-1 items-center justify-end overflow-hidden max-md:hidden" id="header-info">
      <div className="flex items-center gap-2">
      {source && <Tip tip={t('editor.importedTip', { src: source.repo_url || 'zip', ref: source.ref })}><Badge variant="secondary" className="gap-1"><GitFork className="size-3" />{t('editor.imported')}</Badge></Tip>}
      <Badge variant="secondary" className="hidden @[7rem]:inline-flex" id="llm-mode-badge">{t('editor.llmMode', { mode })}</Badge>
      {wid && <Badge variant="outline" className="hidden @[16rem]:inline-flex" id="wid-badge">{t('editor.idBadge', { id: wid })}</Badge>}
      </div></div>
      <div className="contents max-md:hidden"><PendingBadge /><NotificationBell /><LanguageSwitcher /><ThemeToggle /><UserMenu /></div>
      </div>
    </header>
}
