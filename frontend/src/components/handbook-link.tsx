/** Inline link to a handbook page in the user's language, opened in a new tab (TASK-0260). */
import { useTranslation } from 'react-i18next'
import { ExternalLink } from 'lucide-react'
import { handbookUrl } from '@/lib/handbook'

export function HandbookLink({ page, anchor, label, ariaLabel, id }: { page: string; anchor?: string; label: string; ariaLabel?: string; id?: string }) {
  const { i18n, t } = useTranslation()
  return <a id={id} href={handbookUrl(page, i18n.resolvedLanguage, anchor)} target="_blank" rel="noopener noreferrer"
    aria-label={`${ariaLabel || label} (${t('docs.newTab')})`}
    className="inline-flex items-center gap-1 underline underline-offset-4 hover:text-foreground">
    {label}<ExternalLink className="size-3" aria-hidden="true" /></a>
}
