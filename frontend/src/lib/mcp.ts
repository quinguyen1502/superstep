/** MCP servers (TASK-0013): API types shared by the settings section and the MCP node settings. */
export type McpTool = { name: string; description: string; input_schema: { properties?: Record<string, { type?: string; description?: string }>; required?: string[] } }
export type McpServer = { id: string; name: string; scope: 'user' | 'org'; transport: 'stdio' | 'http' | 'managed'; command: string | null; args: string[]; url: string | null
  adapter?: string | null; settings?: Record<string, string | number>
  secrets: Record<string, string>; tools: McpTool[]; tools_at: number | null; created: number; can_edit: boolean }
export type ManagedAdapter = { id: string; settings_schema: { properties: Record<string, { type: string; format?: string; default?: string | number; resource_kind?: string }> }; secret_fields: string[] }
export type McpList = { servers: McpServer[]; is_admin: boolean; stdio_enabled: boolean; org_usable?: boolean; managed_adapters?: ManagedAdapter[] }
