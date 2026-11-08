import { useCallback, useEffect, useState } from 'react'
import { Pressable, Text, View } from 'react-native'
import { StatusBar } from 'expo-status-bar'
import * as DocumentPicker from 'expo-document-picker'
import { Chat } from '@superstep/react-native'
import { createHostClient, type HostSession } from './src/host'
import { line, type ExampleLocale } from './src/labels'

const origin = process.env.EXPO_PUBLIC_HOST_URL ?? 'http://localhost:5188'
const people = [
  { id: 'lan', name: 'Lan' },
  { id: 'minh', name: 'Minh' },
] as const

function messageOf(error: unknown, locale: ExampleLocale): string {
  if (error instanceof Error && error.message === 'COOKIE') return line(locale, 'cookie')
  return error instanceof Error ? error.message : String(error)
}

export default function App() {
  const [locale, setLocale] = useState<ExampleLocale>('en')
  const [host] = useState(() => createHostClient(origin))
  const [session, setSession] = useState<HostSession | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    let live = true
    void host.session().then(
      value => { if (live) setSession(value) },
      reason => { if (live) setError(messageOf(reason, locale)) },
    )
    return () => { live = false }
  }, [host, locale])
  const signIn = (persona: 'lan' | 'minh') => {
    setBusy(true)
    setError(null)
    void host.login(persona).then(setSession, reason => setError(messageOf(reason, locale))).finally(() => setBusy(false))
  }
  const signOut = () => {
    setBusy(true)
    setError(null)
    void host.logout().then(
      () => setSession(current => current && { ...current, user: null }),
      reason => setError(messageOf(reason, locale)),
    ).finally(() => setBusy(false))
  }
  const pickFile = useCallback(async () => {
    const result = await DocumentPicker.getDocumentAsync({ copyToCacheDirectory: true, multiple: false })
    if (result.canceled || !result.assets[0]) return null
    const file = result.assets[0]
    return { uri: file.uri, name: file.name, type: file.mimeType || 'application/octet-stream' }
  }, [])
  const ready = session?.user && session.config.baseUrl && session.config.slug
  return <View style={{ flex: 1, backgroundColor: '#ffffff' }}>
    <StatusBar style="dark" />
    <View style={{ paddingTop: 48, paddingHorizontal: 16, paddingBottom: 12, gap: 8 }}>
      <Text style={{ fontSize: 20, fontWeight: '700', color: '#1c1917' }}>{line(locale, 'title')}</Text>
      <Text style={{ color: '#78716c' }}>{line(locale, 'demo')}</Text>
      <View style={{ flexDirection: 'row', gap: 12 }}>
        <Pressable accessibilityRole="button" accessibilityLabel={line(locale, 'language')} onPress={() => setLocale(value => value === 'en' ? 'vi' : 'en')}>
          <Text style={{ color: '#1d4ed8' }}>{locale === 'en' ? line(locale, 'vietnamese') : line(locale, 'english')}</Text>
        </Pressable>
        {session?.user && <Pressable accessibilityRole="button" accessibilityLabel={line(locale, 'signOut')} disabled={busy} onPress={signOut}>
          <Text style={{ color: '#1c1917' }}>{line(locale, 'signOut')} ({session.user.name})</Text>
        </Pressable>}
      </View>
      {error && <Text accessibilityRole="alert" style={{ color: '#b91c1c' }}>{error}</Text>}
    </View>
    {!session && !error && <Text style={{ padding: 16, color: '#78716c' }}>{line(locale, 'loading')}</Text>}
    {session && !session.user && <View style={{ padding: 16, gap: 12 }}>
      {people.map(person => <Pressable
        key={person.id}
        accessibilityRole="button"
        accessibilityLabel={`${line(locale, 'signIn')} ${person.name}`}
        disabled={busy}
        onPress={() => signIn(person.id)}
        style={{ borderWidth: 1, borderColor: '#e7e5e4', borderRadius: 12, padding: 14 }}
      >
        <Text style={{ color: '#1c1917' }}>{line(locale, 'signIn')} {person.name}</Text>
      </Pressable>)}
    </View>}
    {session?.user && !ready && <Text style={{ padding: 16, color: '#b91c1c' }}>{line(locale, 'missing')}</Text>}
    {ready && session.user && <Chat
      key={session.user.id}
      style={{ flex: 1 }}
      slug={session.config.slug}
      baseUrl={session.config.baseUrl}
      locale={locale}
      getToken={host.token}
      pickFile={pickFile}
    />}
  </View>
}
