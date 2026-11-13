/** The Code tab's export languages: Python or LangGraph.js TypeScript. */
export const EXPORT_LANGUAGES = ['python', 'typescript'] as const
export type ExportLanguage = typeof EXPORT_LANGUAGES[number]
export const EXPORT_LANGUAGE_KEY = 'codeView.language'

const isLanguage = (v: unknown): v is ExportLanguage => (EXPORT_LANGUAGES as readonly unknown[]).includes(v)

/** The language picked last time (stored per browser), else Python. */
export function savedExportLanguage(storage: Pick<Storage, 'getItem'> | undefined = globalThis.localStorage): ExportLanguage {
  try { const v = storage?.getItem(EXPORT_LANGUAGE_KEY); return isLanguage(v) ? v : 'python' } catch { return 'python' }
}

export function saveExportLanguage(v: ExportLanguage, storage: Pick<Storage, 'setItem'> | undefined = globalThis.localStorage) {
  try { storage?.setItem(EXPORT_LANGUAGE_KEY, v) } catch { /* private mode: not remembered */ }
}

export const exportUrl = (wid: string, language: ExportLanguage) => `/api/workflows/${encodeURIComponent(wid)}/code?language=${language}`
export const fileExtension = (language: ExportLanguage) => (language === 'typescript' ? 'ts' : 'py')
/** The runnable LangGraph project (zip with langgraph.json) for `langgraph dev` and LangSmith Studio. */
export const projectUrl = (wid: string, language: ExportLanguage) => `/api/workflows/${encodeURIComponent(wid)}/export/${language}/project`

export type ProjectBindingChoice = { name: string; backend: string; snapshot: boolean }

/** Project zip URL. Backend and snapshot choices stay in the query so the graph file itself does not change. */
export function projectDownloadUrl(wid: string, language: ExportLanguage, choices: ProjectBindingChoice[] = []): string {
  const url = new URL(projectUrl(wid, language), 'http://local')
  for (const choice of choices) {
    url.searchParams.append('backend', `${choice.name}:${choice.backend}`)
    if (choice.snapshot) url.searchParams.append('snapshot', choice.name)
  }
  return url.pathname + url.search
}
