/** The portal's React shell is independent of widget.js, which owns its plain-JS bubble and iframe. */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import type { WidgetAPI } from '../../../frontend/src/widget/protocol'
import type { Session } from './app'

export function WidgetDemo({ session, lang, onError }: { session: Session; lang: 'en' | 'vi'; onError: (error: unknown) => void }) {
  const { t } = useTranslation(), [widget, setWidget] = useState<WidgetAPI | null>(null), [ready, setReady] = useState(false)
  const [counts, setCounts] = useState({ messages: 0, answers: 0 }), report = useRef(onError)
  useEffect(() => { report.current = onError }, [onError])
  const { baseUrl, slug } = session.config
  useEffect(() => {
    let active = true
    const script = document.createElement('script'); script.src = new URL('/c/widget.js', baseUrl).href; script.async = true
    window.Superstep = { q: [['init', { slug, baseUrl, open: true }]] }
    script.onload = () => { if (active) setWidget(window.Superstep as WidgetAPI) }
    script.onerror = () => report.current({ code: 'HTTP_ERROR' })
    document.body.append(script)
    return () => { active = false; script.remove() }
  }, [baseUrl, slug])
  useEffect(() => {
    if (!widget) return
    const off = [widget.on('ready', () => setReady(true)), widget.on('error', data => { setReady(false); report.current({ code: data.code }) }),
      widget.on('message', () => setCounts(value => ({ ...value, messages: value.messages + 1 }))),
      widget.on('answer', () => setCounts(value => ({ ...value, answers: value.answers + 1 })))]
    return () => { off.forEach(unsubscribe => unsubscribe()); widget.close() }
  }, [widget])
  useEffect(() => { if (widget) widget.init({ slug, language: lang }) }, [widget, slug, lang])
  useEffect(() => {
    if (!widget) return
    let active = true; setReady(false)
    const operation = session.user
      ? widget.identify(async () => (await api<{ token: string }>('/api/auth/chat-token', { method: 'POST' })).token)
      : widget.logout()
    void operation.catch(error => { if (active) report.current(error) })
    return () => { active = false }
  }, [widget, session.user?.id]) // eslint-disable-line react-hooks/exhaustive-deps -- identity changes, not callback refreshes
  return <Card className="mt-6 max-w-xl" data-testid="widget-demo" data-ready={ready}>
    <CardHeader><CardTitle>{t('chat.toolkit.widgetExample')}</CardTitle><CardDescription>{t('chat.toolkit.widgetDescription')}</CardDescription></CardHeader>
    <CardContent className="flex flex-col gap-4"><p role="status">{t(ready ? 'chat.toolkit.widgetReady' : 'chat.toolkit.loading')}</p>
      <p data-testid="widget-events">{t('chat.toolkit.widgetEvents', counts)}</p>
      <div className="flex items-center gap-2"><Button disabled={!widget} onClick={() => widget?.open()}>{t('chat.toolkit.openWidget')}</Button>
        <Button variant="outline" disabled={!widget} onClick={() => widget?.close()}>{t('chat.toolkit.closeWidget')}</Button></div>
    </CardContent>
  </Card>
}
