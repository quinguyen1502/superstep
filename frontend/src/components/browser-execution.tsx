import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { ShieldAlert } from 'lucide-react'
import { useMcpServers } from '@/lib/use-mcp-servers'
import { browserServer } from '@/lib/browser-tools'
import { object } from '@/lib/browser-settings'

export function BrowserExecution({ connections }: { connections: string[] }) {
  const { t } = useTranslation(), { servers, error } = useMcpServers()
  const selected = servers?.filter(server => connections.includes(server.id) && browserServer(server)) || []
  if (error) return <p className="text-xs text-destructive" role="alert">{error}</p>
  if (!selected.length) return null
  return <div className="space-y-3" id="browser-execution"><Separator />
    <Alert variant="warning"><ShieldAlert /><AlertDescription>{t('browserTools.executionHelp')}</AlertDescription></Alert>
    {selected.map(server => { const settings = object(server.settings); return <div key={server.id} className="space-y-1 rounded-md border p-3 text-xs">
      <p className="font-medium">{server.name}</p><p className="text-muted-foreground">{t('browserTools.limits', { actions: settings.max_actions ?? 12, timeout: settings.action_timeout_ms ?? 30000, idle: settings.idle_timeout_s ?? 120, lifetime: settings.lifetime_s ?? 600 })}</p>
    </div> })}
  </div>
}
