import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { fmtCount, fmtShare, type UsageQuality } from '@/lib/usage'

export function UsageQualityCard({ quality }: { quality: UsageQuality }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage
  const date = new Intl.DateTimeFormat(lang, { dateStyle: 'medium' })
  return <Card id="usage-quality">
    <CardHeader>
      <CardTitle>{t('settings.usage.quality.title')}</CardTitle>
      <CardDescription>{t('settings.usage.quality.minimum', { count: quality.minimum_ratings })}</CardDescription>
    </CardHeader>
    <CardContent className="space-y-6">
      <section className="space-y-2" aria-labelledby="usage-quality-ratings">
        <h3 id="usage-quality-ratings" className="font-medium">{t('settings.usage.quality.ratings')}</h3>
        {quality.ratings.length ? <Table>
          <TableHeader><TableRow><TableHead>{t('settings.usage.col.workflow')}</TableHead>
            <TableHead className="text-right">{t('settings.usage.quality.samples')}</TableHead>
            <TableHead className="text-right">{t('settings.usage.quality.thumbsDown')}</TableHead></TableRow></TableHeader>
          <TableBody>{quality.ratings.map(row => <TableRow key={row.workflow_id}>
            <TableCell>{row.name ?? row.workflow_id}</TableCell>
            <TableCell className="text-right tabular-nums">{fmtCount(row.ratings, lang)}</TableCell>
            <TableCell className="text-right tabular-nums">{row.thumbs_down_share === null
              ? t('settings.usage.quality.insufficient') : fmtShare(row.thumbs_down_share, lang)}</TableCell>
          </TableRow>)}</TableBody>
        </Table> : <p className="text-sm text-muted-foreground">{t('settings.usage.quality.noRatings')}</p>}
      </section>
      <section className="space-y-2" aria-labelledby="usage-quality-suites">
        <h3 id="usage-quality-suites" className="font-medium">{t('settings.usage.quality.suites')}</h3>
        {quality.suites.length ? <Table>
          <TableHeader><TableRow><TableHead>{t('settings.usage.col.workflow')}</TableHead>
            <TableHead>{t('settings.usage.quality.completed')}</TableHead>
            <TableHead className="text-right">{t('settings.usage.quality.passRate')}</TableHead></TableRow></TableHeader>
          <TableBody>{quality.suites.map(row => <TableRow key={row.workflow_id}>
            <TableCell>{row.name ?? row.workflow_id}</TableCell>
            <TableCell>{date.format(row.ended * 1000)}</TableCell>
            <TableCell className="text-right tabular-nums">{row.total ? t('settings.usage.quality.result', {
              rate: fmtShare(row.passed / row.total, lang), passed: fmtCount(row.passed, lang), total: fmtCount(row.total, lang),
            }) : '—'}</TableCell>
          </TableRow>)}</TableBody>
        </Table> : <p className="text-sm text-muted-foreground">{t('settings.usage.quality.noSuites')}</p>}
      </section>
      {quality.langsmith_configured && <Link to="/settings/users#langsmith-settings" className="text-sm underline underline-offset-4">
        {t('settings.usage.quality.langsmith')}
      </Link>}
    </CardContent>
  </Card>
}
