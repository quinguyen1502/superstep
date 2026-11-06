import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useConfirmDelete } from './use-confirm-delete'
import { useMcpServers } from '@/lib/use-mcp-servers'
import { browserServer, type BrowserRecipe } from '@/lib/browser-tools'
import type { TemplateField } from './template-editor'

type Props = { value?: BrowserRecipe; onChange: (value: BrowserRecipe | undefined) => void }
/** A recipe is the existing workflow; Start hosts its root contract, never a second store. */
export function BrowserRecipeSettings({ value, name, onChange }: Props & { name: string }) {
  const { t } = useTranslation(), confirm = useConfirmDelete(), { servers, error } = useMcpServers()
  const available = servers?.filter(browserServer) || []
  return <div className="space-y-3" id="browser-recipe-settings">
    <div className="flex items-center justify-between gap-2"><Label htmlFor="browser-recipe-enabled">{t('browserTools.recipe')}</Label>
      <Switch id="browser-recipe-enabled" checked={!!value} onCheckedChange={enabled => enabled ? onChange({ version: 1, connection_id: '', inputs: [], outputs: [] }) : confirm.ask({ name, title: t('browserTools.disableRecipeTitle', { name }), description: t('browserTools.disableRecipeBody'), onConfirm: () => onChange(undefined) })} /></div>
    <p className="text-xs text-muted-foreground">{t('browserTools.recipeHelp')}</p>
    {value && <div className="space-y-1.5"><Label htmlFor="browser-recipe-connection">{t('editor.mcpServer')}</Label>
      <Select value={value.connection_id || undefined} onValueChange={connection_id => onChange({ ...value, connection_id })}><SelectTrigger className="w-full" id="browser-recipe-connection"><SelectValue placeholder={t('common.choose')} /></SelectTrigger>
        <SelectContent emptyMessage={error || (servers === null ? t('common.loading') : undefined)}>{available.map(server => <SelectItem key={server.id} value={server.id}>{server.name}</SelectItem>)}</SelectContent></Select>
      <p className="text-xs text-muted-foreground">{t('browserTools.recipeConnectionHelp')}</p>
    </div>}
    {error && <p role="alert" className="text-xs text-destructive">{error}</p>}{confirm.dialog}
  </div>
}

export function BrowserRecipeData({ value, fields, onChange }: Props & { fields: TemplateField[] }) {
  const { t } = useTranslation()
  if (!value) return <p className="text-xs text-muted-foreground">{t('browserTools.enableRecipeHelp')}</p>
  const toggle = (kind: 'inputs' | 'outputs', name: string, enabled: boolean) => onChange({ ...value, [kind]: enabled ? [...value[kind], name] : value[kind].filter(item => item !== name) })
  return <div className="space-y-4" id="browser-recipe-data">{(['inputs', 'outputs'] as const).map(kind => {
    const available = fields.filter(field => kind === 'inputs' ? ['string', 'number', 'integer', 'boolean'].includes(field.type || '') : field.type === 'object')
    return <div className="space-y-2" key={kind}><p className="text-xs font-medium">{t(`browserTools.recipe${kind === 'inputs' ? 'Inputs' : 'Outputs'}`)}</p>
      <p className="text-xs text-muted-foreground">{t(`browserTools.recipe${kind === 'inputs' ? 'InputHelp' : 'OutputHelp'}`)}</p>
      {available.map(field => <div key={field.name} className="flex items-center justify-between gap-2"><Label htmlFor={`recipe-${kind}-${field.name}`} className="min-w-0 wrap-anywhere font-mono">{field.name}</Label>
        <Switch id={`recipe-${kind}-${field.name}`} checked={value[kind].includes(field.name)} onCheckedChange={enabled => toggle(kind, field.name, enabled)} /></div>)}
      {!available.length && <p className="text-xs text-muted-foreground">{t('browserTools.recipeNoFields')}</p>}
      {!value[kind].length && <p role="alert" className="text-xs text-destructive">{t('browserTools.recipeFieldRequired')}</p>}
    </div>
  })}</div>
}
