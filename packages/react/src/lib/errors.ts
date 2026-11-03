import i18n, { type i18n as I18n } from 'i18next'

export type ApiErrorBody = { code?: string; message?: string; details?: any }

/** The one place that turns an API/WS error into user text: translated by code, else the server's English message. */
export function errorText(e: ApiErrorBody, translator: Pick<I18n, 'exists' | 't'> = i18n): string {
  const key = `errors.${e.code}`
  const params = e.details && typeof e.details === 'object' && !Array.isArray(e.details) ? e.details : {}
  return String(e.code && translator.exists(key) ? translator.t(key, params) : e.message || translator.t("errors.HTTP_ERROR"))
}

