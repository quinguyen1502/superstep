import { createContext, useContext, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import { createInstance } from 'i18next'
import { I18nextProvider } from 'react-i18next'
import { TooltipProvider } from '../ui/tooltip.js'
import { ChatPresentationProvider } from '../components/presentation.js'
import { messages as resources } from './messages.generated.js'
import type { ChatController } from './use-chat.js'

export type ChatLocale = 'en' | 'vi'
export type ChatMessages = Record<string, string>
export interface ChatTheme { primary?: string; primaryForeground?: string; radius?: string | number; font?: string; colorScheme?: 'light' | 'dark' | 'system' }
export interface ChatProviderProps { chat?: ChatController; locale?: ChatLocale; messages?: ChatMessages; theme?: ChatTheme; children: ReactNode; className?: string; style?: CSSProperties }
const Controller = createContext<ChatController | null>(null)
export function useChatController(explicit?: ChatController) {
  const current = useContext(Controller)
  if (!explicit && !current) throw new Error('Wrap chat components in ChatProvider or pass a chat controller')
  return explicit ?? current!
}

export function ChatProvider({ chat, locale = 'en', messages, theme, children, className, style }: ChatProviderProps) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null), [system, setSystem] = useState<'light' | 'dark'>('light')
  const i18n = useMemo(() => {
    const instance = createInstance()
    const data = JSON.parse(JSON.stringify(resources)) as Record<ChatLocale, object>
    void instance.init({ lng: locale, fallbackLng: 'en', initAsync: false, resources: { en: { translation: data.en }, vi: { translation: data.vi } }, interpolation: { escapeValue: false }, react: { useSuspense: false } })
    for (const [key, value] of Object.entries(messages ?? {})) instance.addResource(locale, 'translation', key, value)
    return instance
  }, [locale, messages])
  useEffect(() => {
    if (typeof matchMedia !== 'function') return
    const query = matchMedia('(prefers-color-scheme: dark)'), apply = () => setSystem(query.matches ? 'dark' : 'light')
    apply(); query.addEventListener('change', apply); return () => query.removeEventListener('change', apply)
  }, [])
  const scheme = !theme?.colorScheme || theme.colorScheme === 'system' ? system : theme.colorScheme
  const vars = { ...(theme?.primary ? { '--ss-primary': theme.primary } : {}), ...(theme?.primaryForeground ? { '--ss-primary-foreground': theme.primaryForeground } : {}),
    ...(theme?.radius !== undefined ? { '--ss-radius': typeof theme.radius === 'number' ? `${theme.radius}px` : theme.radius } : {}), ...(theme?.font ? { '--ss-font': theme.font } : {}), ...style } as CSSProperties
  return <I18nextProvider i18n={i18n}><Controller.Provider value={chat ?? null}>
    <div ref={setContainer} className={`superstep-chat ${className ?? ''}`} style={vars} lang={locale} data-color-scheme={scheme}>
      <ChatPresentationProvider value={{ portalContainer: container }}><TooltipProvider>{children}</TooltipProvider></ChatPresentationProvider>
    </div>
  </Controller.Provider></I18nextProvider>
}
