/** Overridable colours for a host app. This package does not use Studio CSS tokens. */
export interface ChatTheme {
  background: string
  foreground: string
  muted: string
  surface: string
  userBubble: string
  userText: string
  assistantBubble: string
  assistantText: string
  border: string
  accent: string
  danger: string
  code: string
  radius: number
  fontSize: number
}

export const defaultTheme: ChatTheme = {
  background: '#ffffff',
  foreground: '#1c1917',
  muted: '#78716c',
  surface: '#f5f5f4',
  userBubble: '#1c1917',
  userText: '#fafaf9',
  assistantBubble: '#f5f5f4',
  assistantText: '#1c1917',
  border: '#e7e5e4',
  accent: '#1d4ed8',
  danger: '#b91c1c',
  code: '#f5f5f4',
  radius: 12,
  fontSize: 16,
}

export function themeOf(override?: Partial<ChatTheme>): ChatTheme {
  return { ...defaultTheme, ...override }
}
