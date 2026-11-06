import { useEffect, useState } from 'react'
import { api } from './api'
import type { McpList, McpServer } from './mcp'

export function useMcpServers() {
  const [servers, setServers] = useState<McpServer[] | null>(null), [error, setError] = useState('')
  useEffect(() => { api<McpList>('/api/mcp/servers').then(value => setServers(value.servers)).catch(error => { setServers([]); setError(error.message) }) }, [])
  return { servers, setServers, error, setError }
}
