import { describe, expect, it } from 'vitest'
import { EXPORT_LANGUAGE_KEY, exportUrl, fileExtension, projectUrl, saveExportLanguage, savedExportLanguage } from '@/lib/code-export'
import en from '@/locales/en.json'
import vi from '@/locales/vi.json'

const store = (v: string | null) => ({ getItem: () => v })

describe('Code tab export language (TASK-0082)', () => {
  it('defaults to Python and remembers a valid choice only', () => {
    expect(savedExportLanguage(store(null))).toBe('python')
    expect(savedExportLanguage(store('typescript'))).toBe('typescript')
    expect(savedExportLanguage(store('rust'))).toBe('python')
    expect(savedExportLanguage({ getItem: () => { throw new Error('denied') } })).toBe('python')
    const saved: Record<string, string> = {}
    saveExportLanguage('typescript', { setItem: (k, v) => { saved[k] = v } })
    expect(saved[EXPORT_LANGUAGE_KEY]).toBe('typescript')
  })
  it('asks the API for the language and names the file', () => {
    expect(exportUrl('w 1', 'typescript')).toBe('/api/workflows/w%201/code?language=typescript')
    expect(fileExtension('typescript')).toBe('ts'); expect(fileExtension('python')).toBe('py')
    expect(projectUrl('w 1', 'python')).toBe('/api/workflows/w%201/export/python/project')
  })
  it('has en/vi strings for the picker and the download button', () => {
    expect(en.codeView.download).toBe('Download .{{ext}}'); expect(vi.codeView.download).toBe('Tải .{{ext}}')
    expect(vi.codeView.languageLabel).toBe('Ngôn ngữ')
    expect(en.codeView.downloadProject).toBe('Project .zip'); expect(vi.codeView.downloadProject).toBe('Dự án .zip')
    expect(en.errors.EXPORT_LANGUAGE_UNSUPPORTED).toBeTruthy(); expect(vi.errors.TYPESCRIPT_EXPORT_UNAVAILABLE).toBeTruthy()
  })
})
