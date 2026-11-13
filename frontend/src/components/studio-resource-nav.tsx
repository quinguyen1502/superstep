import { Database, Workflow } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export function StudioResourceNav({ active }: { active: 'workflows' | 'datasets' }) {
  const { t } = useTranslation()
  return <nav aria-label={t('dataset.navigation')} className="flex items-center gap-1">
    <Button variant={active === 'workflows' ? 'secondary' : 'ghost'} asChild>
      <Link to="/workflows" aria-current={active === 'workflows' ? 'page' : undefined}><Workflow aria-hidden="true" />{t('list.title')}</Link>
    </Button>
    <Button variant={active === 'datasets' ? 'secondary' : 'ghost'} asChild>
      <Link to="/datasets" aria-current={active === 'datasets' ? 'page' : undefined}><Database aria-hidden="true" />{t('dataset.title')}</Link>
    </Button>
  </nav>
}
