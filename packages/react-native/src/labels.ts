import en from './locales/en.json'
import vi from './locales/vi.json'

export type ChatLocale = 'en' | 'vi'

// The label catalogs: one JSON file per language with the same keys.
const copy = { en, vi } as const

export type LabelKey = keyof typeof copy.en

export function text(locale: ChatLocale | undefined, key: LabelKey): string {
  return copy[locale === 'vi' ? 'vi' : 'en'][key]
}
