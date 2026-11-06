import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { BrowserUrlBinding } from './browser-url-binding'
import { useMcpServers } from '@/lib/use-mcp-servers'
import { urlTool } from '@/lib/browser-tools'
import type { AgentTool } from '@/lib/agent'
import type { TemplateField } from './template-editor'

export function AgentBrowserData({ tools, fields, readOnly, onChange }: { tools: AgentTool[]; fields: TemplateField[]; readOnly?: boolean; onChange: (tools: AgentTool[]) => void }) {
  const { t } = useTranslation(), { servers, error } = useMcpServers()
  const selected = tools.map((tool, index) => ({ tool, index })).filter(({ tool }) => tool.source === 'mcp' && urlTool(servers?.find(server => server.id === tool.server_id), tool.tool))
  if (error) return <p className="text-xs text-destructive" role="alert">{error}</p>
  if (!selected.length) return null
  return <div className="space-y-3" id="agent-browser-data"><Separator /><p className="text-xs font-medium">{t('browserTools.bindings')}</p>
    {selected.map(({ tool, index }) => <div key={`${index}-${tool.name}`} className="space-y-2 rounded-md border p-3"><Badge variant="outline">{tool.name}</Badge>
      <BrowserUrlBinding id={`agent-tool-${index}-url`} value={tool.url_binding} fields={fields} readOnly={readOnly} onChange={url_binding => onChange(tools.map((item, position) => position === index ? { ...item, url_binding } : item))} />
    </div>)}
  </div>
}
