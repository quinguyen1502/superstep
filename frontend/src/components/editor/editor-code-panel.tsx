import { useEffect, useState } from 'react'
import { Check, Copy, Download, FileArchive } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { CodeEditor, type LineRange } from '@/components/code-editor'
import { api } from '@/lib/api'
import { EXPORT_LANGUAGES, exportUrl, fileExtension, projectUrl, saveExportLanguage, savedExportLanguage, type ExportLanguage } from '@/lib/code-export'
import { useStudioCtx } from './studio-context'

type CodeExport = { language: ExportLanguage; media_type: string; filename: string; version: number | null; code: string; nodes: Record<string, LineRange[]> }

/** Code tab (TASK-0071, REQ-0043): the saved workflow as LangGraph code, in Python or as LangGraph.js TypeScript
 * (TASK-0082, REQ-0047; the choice is remembered), or as a LangGraph project zip for `langgraph dev`; the node selected on the canvas shows where it is in the code. */
export function EditorCodePanel() {
  const { t } = useTranslation()
  const { wid, saves, selNode, isDirty } = useStudioCtx()
  const [out, setOut] = useState<CodeExport | null>(null); const [err, setErr] = useState(''); const [copied, setCopied] = useState(false)
  const [language, setLanguage] = useState<ExportLanguage>(() => savedExportLanguage())
  const pick = (v: ExportLanguage) => { setLanguage(v); saveExportLanguage(v) }
  useEffect(() => {
    if (!wid) return
    let live = true
    // a refused export (an Agent node in TypeScript, TASK-0119) must not leave the other language's file behind
    api<CodeExport>(exportUrl(wid, language)).then(d => { if (live) { setOut(d); setErr('') } }).catch(e => { if (live) { setOut(null); setErr(e.message) } })
    return () => { live = false }
  }, [wid, saves, language])
  if (!wid) return <p className="p-3 text-xs text-muted-foreground" id="code-save-first">{t('codeView.saveFirst')}</p>
  const marks = selNode && out ? out.nodes[selNode.id] ?? [] : []
  const copy = () => { if (!out) return; void navigator.clipboard?.writeText(out.code); setCopied(true); setTimeout(() => setCopied(false), 1500) }
  const download = () => {
    if (!out) return
    const url = URL.createObjectURL(new Blob([out.code], { type: out.media_type || 'text/plain' }))
    const a = document.createElement('a'); a.href = url; a.download = out.filename; a.click(); URL.revokeObjectURL(url)
  }
  return <div className="h-full min-h-0 flex flex-col gap-2 p-3">
    <div className="flex min-w-0 items-center gap-2 text-xs">
      <Select value={language} onValueChange={v => pick(v as ExportLanguage)}>
        <SelectTrigger size="sm" className="w-32 shrink-0" id="code-export-language" aria-label={t('codeView.languageLabel')}><SelectValue /></SelectTrigger>
        <SelectContent>{EXPORT_LANGUAGES.map(l => <SelectItem key={l} value={l} id={`code-export-language-${l}`}>{t(`code.languages.${l}`)}</SelectItem>)}</SelectContent>
      </Select>
      <span className="truncate font-mono" id="code-file">{out?.filename}</span>
      {out?.version != null && <Badge variant="secondary" id="code-version">{t('codeView.version', { n: out.version })}</Badge>}
      {isDirty() && <Badge variant="outline" className="border-warning text-warning" id="code-unsaved">{t('codeView.unsaved')}</Badge>}
      <span className="ml-auto truncate text-muted-foreground" id="code-hint">
        {selNode ? (marks.length ? t('codeView.showing', { node: (selNode.data as any)?.label || selNode.id }) : t('codeView.noCode')) : t('codeView.selectHint')}</span>
      <Button size="sm" variant="outline" id="code-copy" disabled={!out} onClick={copy}>{copied ? <Check /> : <Copy />}{t('common.copy')}</Button>
      <Button size="sm" variant="outline" id="code-download" disabled={!out} onClick={download}><Download />{t('codeView.download', { ext: fileExtension(language) })}</Button>
      <Tooltip>
        <TooltipTrigger asChild>{out
          ? <Button size="sm" variant="outline" id="code-download-project" asChild><a href={projectUrl(wid, language)} download><FileArchive />{t('codeView.downloadProject')}</a></Button>
          : <Button size="sm" variant="outline" id="code-download-project" disabled><FileArchive />{t('codeView.downloadProject')}</Button>}</TooltipTrigger>
        <TooltipContent>{t('codeView.downloadProjectTip')}</TooltipContent>
      </Tooltip>
    </div>
    {err && <Alert variant="destructive"><AlertDescription>{err}</AlertDescription></Alert>}
    <CodeEditor readOnly language={out?.language ?? language} value={out?.language === language ? out.code : ''} marks={out?.language === language ? marks : []}
      id="code-view" className="flex-1" />
  </div>
}
