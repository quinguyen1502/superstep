import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import en from '@/locales/en.json'
import vi from '@/locales/vi.json'

export const LANGS = ['en', 'vi'] as const
export const LANG_KEY = 'lang'

i18n.use(LanguageDetector).use(initReactI18next).init({
  resources: { en: { translation: en }, vi: { translation: vi } },
  supportedLngs: LANGS, nonExplicitSupportedLngs: true, fallbackLng: 'en', interpolation: { escapeValue: false },
  detection: { order: ['localStorage', 'navigator'], lookupLocalStorage: LANG_KEY, caches: ['localStorage'] },
})
const syncHtmlLang = (l: string) => { document.documentElement.lang = l }
syncHtmlLang(i18n.resolvedLanguage || 'en'); i18n.on('languageChanged', syncHtmlLang)

export type ApiErrorBody = { code?: string; message?: string; details?: any }

/** The one place that turns an API/WS error into user text: translated by code, else the server's English message. */
export function errorText(e: ApiErrorBody): string {
  const key = `errors.${e.code}`
  const params = e.details && typeof e.details === 'object' && !Array.isArray(e.details) ? e.details : {}
  return String(e.code && i18n.exists(key) ? i18n.t(key, params) : e.message || i18n.t("errors.HTTP_ERROR"))
}

/** The code of one validation message, sent next to the English `errors` (TASK-0132); null when it has none. */
export type Issue = { code: string; params?: Record<string, unknown> } | null

/** Validation messages in the UI language: `validation.<code>` when the API sent a code we know, else the English text. */
export function issueTexts(errors: string[], issues?: Issue[]): string[] {
  return errors.map((message, i) => {
    const issue = issues?.[i]; const key = `validation.${issue?.code}`
    return issue?.code && i18n.exists(key) ? i18n.t(key, issue.params ?? {}) : message
  })
}

/** Codes whose `errors` list carries the specific (dynamic) messages: validator issues, node exceptions. */
const DYNAMIC = new Set(['WORKFLOW_INVALID', 'NODE_FAILED', 'RUN_FAILED'])
export function eventErrors(ev: { error?: ApiErrorBody; errors?: string[]; issues?: Issue[] }): string[] {
  if (!ev.error || DYNAMIC.has(ev.error.code || '')) return ev.errors ? issueTexts(ev.errors, ev.issues) : ev.error ? [errorText(ev.error)] : []
  return [errorText(ev.error)]
}

export const fmtDate = (t: number) => new Date(t * 1000).toLocaleString(i18n.resolvedLanguage)
/** The UI language sent with run and chat requests, so offline (mock) answers match it. */
export const uiLocale = (): string => i18n.resolvedLanguage ?? 'en'
export default i18n
