import type { McpServer } from './mcp'
export type UrlBinding = { source: 'model' | 'fixed' | 'state'; value?: string }
export type BrowserRecipe = { version: 1; connection_id: string; inputs: string[]; outputs: string[] }
export type RecipeTarget = { observation_field: string; role: string; text?: string }
export const urlTool = (server: McpServer | undefined, operation?: string) => server?.transport === 'managed' && (server.adapter === 'browser' && operation === 'navigate' || server.adapter === 'web' && operation === 'fetch')
export const browserServer = (server: McpServer | undefined) => server?.transport === 'managed' && server.adapter === 'browser'
