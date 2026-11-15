import { useState } from 'react'
import { Pressable, Text, TextInput, View } from 'react-native'
import type { NativeChatFile } from '@superstep/sdk/chat'
import { text, type ChatLocale } from './labels.js'
import { themeOf, type ChatTheme } from './theme.js'
import type { ChatController } from './use-chat.js'

export interface ComposerProps {
  chat: Pick<ChatController, 'busy' | 'status' | 'pendingFiles' | 'send' | 'upload' | 'removeFile' | 'cancel'>
  locale?: ChatLocale
  theme?: Partial<ChatTheme>
  pickFile?: () => Promise<NativeChatFile | null>
}

export function Composer({ chat, locale, theme, pickFile }: ComposerProps) {
  const colors = themeOf(theme)
  const [draft, setDraft] = useState('')
  const streaming = chat.status === 'streaming'
  const send = () => {
    const value = draft.trim()
    if (!value || chat.busy) return
    setDraft('')
    void chat.send(value).catch(() => setDraft(value))
  }
  const attach = () => {
    if (!pickFile || chat.busy) return
    void pickFile().then(file => { if (file) return chat.upload(file) }).catch(() => {})
  }
  return <View testID="composer" style={{ borderTopWidth: 1, borderTopColor: colors.border, padding: 12, gap: 8, backgroundColor: colors.background }}>
    {chat.pendingFiles.map(file => <View key={file.id} style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
      <Text style={{ color: colors.foreground, flex: 1 }}>{file.name}</Text>
      <Pressable accessibilityRole="button" accessibilityLabel={`${text(locale, 'remove')} ${file.name}`} onPress={() => { void chat.removeFile(file.id).catch(() => {}) }}>
        <Text style={{ color: colors.accent }}>{text(locale, 'remove')}</Text>
      </Pressable>
    </View>)}
    <TextInput
      accessibilityLabel={text(locale, 'message')}
      value={draft}
      editable={!chat.busy}
      multiline
      maxLength={8000}
      placeholder={text(locale, 'message')}
      placeholderTextColor={colors.muted}
      onChangeText={setDraft}
      style={{ minHeight: 44, maxHeight: 120, borderWidth: 1, borderColor: colors.border, borderRadius: colors.radius, padding: 8, color: colors.foreground, fontSize: colors.fontSize }}
    />
    <View style={{ flexDirection: 'row', justifyContent: 'flex-end', gap: 8 }}>
      {pickFile && <Pressable accessibilityRole="button" accessibilityLabel={text(locale, 'attach')} disabled={chat.busy} onPress={attach}>
        <Text style={{ color: colors.accent }}>{text(locale, 'attach')}</Text>
      </Pressable>}
      {streaming
        ? <Pressable accessibilityRole="button" accessibilityLabel={text(locale, 'stop')} onPress={() => chat.cancel()}>
            <Text style={{ color: colors.danger }}>{text(locale, 'stop')}</Text>
          </Pressable>
        : <Pressable accessibilityRole="button" accessibilityLabel={text(locale, 'send')} disabled={chat.busy || !draft.trim()} onPress={send}>
            <Text style={{ color: colors.accent }}>{text(locale, 'send')}</Text>
          </Pressable>}
    </View>
  </View>
}
