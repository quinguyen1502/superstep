import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, TriangleAlert } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { CodeBlock, CodeBlockActions, CodeBlockContent, CodeBlockCopyButton, CodeBlockHeader, CodeBlockLine, CodeBlockTitle } from '@/components/ui/code-block'
import { CopyField } from '@/components/copy-field'
import { api } from '@/lib/api'
import { useLoadWhen } from '@/lib/use-when'

type Settings = { enabled: boolean; tool: string; path: string }
export const MCP_CLIENTS = ['cursor', 'claude-desktop', 'claude-code'] as const
type Client = typeof MCP_CLIENTS[number]

/** Client config for the MCP server at /mcp (TASK-0114); `token` is the plaintext token when just created. */
export function mcpSnippet(client: Client, url: string, name: string, token = '<token>'): { lang: string; text: string } {
  const key = `superstep-${name.replace(/^run_/, '').replace(/_/g, '-')}`.slice(0, 60)
  if (client === 'claude-code') return { lang: 'bash', text: `claude mcp add --transport http ${key} ${url} \\\n  --header "Authorization: Bearer ${token}"` }
  const server = client === 'cursor' ? { url, headers: { Authorization: `Bearer ${token}` } }
    : { command: 'npx', args: ['-y', 'mcp-remote', url, '--header', 'Authorization:${SUPERSTEP_TOKEN}'], env: { SUPERSTEP_TOKEN: `Bearer ${token}` } }
  return { lang: 'json', text: JSON.stringify({ mcpServers: { [key]: server } }, null, 2) }
}

/** API dialog tab: expose the workflow as an MCP tool and copy a client config. */
export function McpServerTab({ wid, open, token, hasTokens }: { wid?: string; open: boolean; token?: string; hasTokens: boolean }) {
  const { t } = useTranslation()
  const [s, setS] = useState<Settings | null>(null); const [err, setErr] = useState(''); const [client, setClient] = useState<Client>('cursor')
  useLoadWhen(open, () => { setErr(''); wid && api<Settings>(`/api/workflows/${wid}/mcp`).then(setS).catch(e => setErr(e.message)) })
  const toggle = async (enabled: boolean) => {
    setErr('')
    try { setS(await api<Settings>(`/api/workflows/${wid}/mcp`, { method: 'PUT', json: { enabled } })) } catch (e: any) { setErr(e.message) }
  }
  const url = `${location.origin}${s?.path ?? '/mcp'}`
  const snip = s && mcpSnippet(client, url, s.tool, token)
  return <div className="space-y-4" id="mcp-server-tab">
    {err && <Alert variant="destructive"><AlertCircle /><AlertDescription>{err}</AlertDescription></Alert>}
    <div className="flex items-start gap-3 rounded-md border p-3">
      <div className="flex-1 space-y-1"><Label htmlFor="mcp-enabled">{t('mcpServer.enable')}</Label>
        <p className="text-xs text-muted-foreground">{t('mcpServer.enableHelp')}</p></div>
      <Switch id="mcp-enabled" checked={!!s?.enabled} disabled={!s} onCheckedChange={toggle} />
    </div>
    {s?.enabled && <>
      {!hasTokens && <Alert variant="warning" id="mcp-no-token"><TriangleAlert /><AlertDescription>{t('mcpServer.needsToken')}</AlertDescription></Alert>}
      <CopyField id="mcp-url" label={t('mcpServer.url')} value={url} />
      <p className="text-xs text-muted-foreground" id="mcp-tools">{t('mcpServer.tools', { tool: s.tool })}</p>
      <div className="space-y-1.5"><Label htmlFor="mcp-client">{t('mcpServer.client')}</Label>
        <Select value={client} onValueChange={v => setClient(v as Client)}>
          <SelectTrigger id="mcp-client" className="w-full"><SelectValue /></SelectTrigger>
          <SelectContent>{MCP_CLIENTS.map(c => <SelectItem key={c} value={c}>{t(`mcpServer.clients.${c}`)}</SelectItem>)}</SelectContent>
        </Select></div>
      {snip && <CodeBlock size="sm" id="mcp-snippet">
        <CodeBlockHeader><CodeBlockTitle>{t(`mcpServer.where.${client}`)}</CodeBlockTitle><CodeBlockActions><CodeBlockCopyButton value={snip.text} /></CodeBlockActions></CodeBlockHeader>
        <CodeBlockContent>{snip.text.split('\n').map((l, i) => <CodeBlockLine key={i}>{l}</CodeBlockLine>)}</CodeBlockContent>
      </CodeBlock>}
      <p className="text-xs text-muted-foreground">{t('mcpServer.human')}</p>
    </>}
  </div>
}
