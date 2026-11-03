import { StrictMode, version, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Chat, ChatProvider, Composer, MessageList, QuestionCard, useChat } from '@superstep/react'
import type { ChatLocale, ChatTheme } from '@superstep/react'
import { Button } from '@superstep/react/ui/button'
import { api } from './lib/api'
import { messages } from './messages.generated'
import '@superstep/react/styles.css'
import './styles.css'

type Session = { user: { id: string; name: string } | null; config: { baseUrl: string; slug: string } }
function App() {
  const [session, setSession] = useState<Session | null>(null), [locale, setLocale] = useState<ChatLocale>('en'), [scheme, setScheme] = useState<'light' | 'dark' | 'custom'>('light'), [error, setError] = useState(false)
  const t = messages[locale]
  useEffect(() => { void api<Session>('/api/auth/session').then(setSession).catch(() => setError(true)) }, [])
  useEffect(() => { document.title = t.demoTitle }, [t])
  const signIn = async (persona: string) => { setError(false); try { setSession(await api<Session>('/api/auth/login', { persona })) } catch { setError(true) } }
  const theme: ChatTheme = { colorScheme: scheme === 'dark' ? 'dark' : 'light', ...(scheme === 'custom' ? { primary: 'var(--demo-brand)', primaryForeground: 'var(--demo-brand-foreground)', radius: 16, font: 'Georgia, serif' } : {}) }
  return <main lang={locale} className="host-page" data-react-version={version}>
    <nav className="superstep-chat host-controls">{([['/', 'headlessExample'], ['/react/', 'reactExample'], ['/widget.html', 'widgetExample']] as const).map(([href,key]) => <Button key={href} asChild variant="ghost"><a href={href}>{t[key]}</a></Button>)}</nav>
    <header><p className="host-eyebrow">{t.demoTitle}</p><h1>{t.hostTitle}</h1><p>{t.hostDescription}</p></header>
    <div className="superstep-chat host-controls" lang={locale}>
      <div role="group" aria-label={t.language}>{(['en','vi'] as const).map(value => <Button key={value} variant={value === locale ? 'secondary' : 'ghost'} onClick={() => setLocale(value)}>{value === 'en' ? t.english : t.vietnamese}</Button>)}</div>
      <div role="group" aria-label={t.theme}>{(['light','dark','custom'] as const).map(value => <Button key={value} variant={value === scheme ? 'secondary' : 'ghost'} onClick={() => setScheme(value)}>{t[value]}</Button>)}</div>
      <div role="group" aria-label={t.customer}>{(['lan','minh'] as const).map(value => <Button key={value} variant={session?.user?.name.toLowerCase() === value ? 'secondary' : 'outline'} data-testid={`signin-${value}`} onClick={() => void signIn(value)}>{value === 'lan' ? 'Lan' : 'Minh'}</Button>)}</div>
    </div>
    <aside id="host-sentinel" className="border rounded-lg p-3 text-sm"><strong>{t.customTitle}</strong><p>{t.customIntro}</p><button type="button" disabled>{t.hostTitle}</button></aside>
    {error && <p role="alert">{t.requestFailed}</p>}
    {session?.user && <div className="demo-grid">
      <section className="demo-chat" data-testid="main-chat"><Chat {...session.config} identityKey={session.user.id} getToken={async () => (await api<{ token: string }>('/api/auth/chat-token', {})).token} locale={locale} theme={theme} /></section>
      <section className="demo-chat" data-testid="composed-chat"><Composed session={session} locale={locale === 'en' ? 'vi' : 'en'} /></section>
    </div>}
  </main>
}
function Composed({ session, locale }: { session: Session; locale: ChatLocale }) {
  const chat = useChat({ ...session.config, identityKey: session.user!.id, sessionId: null, locale, getToken: async () => (await api<{ token: string }>('/api/auth/chat-token', {})).token })
  return <ChatProvider chat={chat} locale={locale} theme={{ colorScheme: 'dark' }} className="ss-chat" messages={{ 'chat.placeholder': messages[locale].customIntro }}>
    <header className="ss-p-3 ss-border-b ss-font-semibold">{messages[locale].customTitle}</header>
    <MessageList /><QuestionCard /><Composer />
  </ChatProvider>
}
createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
