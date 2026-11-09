import en from './locales/en.json'
import vi from './locales/vi.json'

export type ExampleLocale = 'en' | 'vi'

// The copy catalogs: one JSON file per language with the same keys.
const copy = { en, vi } as const

export type ExampleKey = keyof typeof copy.en

export function line(locale: ExampleLocale, key: ExampleKey): string {
  return copy[locale][key]
}
