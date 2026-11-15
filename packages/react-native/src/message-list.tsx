import type { ReactNode } from 'react'
import { Pressable, ScrollView, Text, View } from 'react-native'
import type { ChatTurn } from '@superstep/sdk/chat'
import { text, type ChatLocale } from './labels.js'
import { MarkdownText } from './markdown.js'
import { themeOf, type ChatTheme } from './theme.js'
import type { ChatController } from './use-chat.js'

export interface MessageListProps {
  chat: Pick<ChatController, 'turns' | 'text' | 'status' | 'pending' | 'rate'>
  locale?: ChatLocale
  theme?: Partial<ChatTheme>
  renderMarkdown?: (value: string) => ReactNode
}

type Row = { key: string; role: 'user' | 'assistant'; body: string; turn?: ChatTurn }

function rowsOf(chat: MessageListProps['chat']): Row[] {
  const rows: Row[] = chat.turns.map(turn => ({ key: turn.id, role: turn.role, body: turn.text, turn }))
  if (chat.pending) rows.push({ key: 'pending', role: 'user', body: chat.pending })
  if (chat.status === 'streaming' && chat.text) rows.push({ key: 'streaming', role: 'assistant', body: chat.text })
  return rows
}

export function MessageList({ chat, locale, theme, renderMarkdown }: MessageListProps) {
  const colors = themeOf(theme)
  const rows = rowsOf(chat)
  return <ScrollView testID="message-list" style={{ flex: 1 }} contentContainerStyle={{ padding: 12, gap: 8 }}>
    {rows.map(row => {
      const mine = row.role === 'user'
      const rating = row.turn?.rating?.value
      return <View key={row.key} style={{ alignSelf: mine ? 'flex-end' : 'flex-start', maxWidth: '90%', gap: 4 }}>
        <Text style={{ color: colors.muted, fontSize: 12 }}>{text(locale, mine ? 'you' : 'assistant')}</Text>
        <View style={{ backgroundColor: mine ? colors.userBubble : colors.assistantBubble, borderRadius: colors.radius, padding: 10 }}>
          {mine
            ? <Text style={{ color: colors.userText, fontSize: colors.fontSize }}>{row.body}</Text>
            : renderMarkdown
              ? renderMarkdown(row.body)
              : <MarkdownText text={row.body} theme={colors} />}
        </View>
        {row.turn?.role === 'assistant' && row.turn.id && <View style={{ flexDirection: 'row', gap: 8 }}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={text(locale, 'helpful')}
            accessibilityState={{ selected: rating === 'up' }}
            onPress={() => { void chat.rate(row.turn!.id, rating === 'up' ? null : 'up').catch(() => {}) }}
          >
            <Text style={{ color: rating === 'up' ? colors.accent : colors.muted }}>{text(locale, 'helpful')}</Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={text(locale, 'notHelpful')}
            accessibilityState={{ selected: rating === 'down' }}
            onPress={() => { void chat.rate(row.turn!.id, rating === 'down' ? null : 'down').catch(() => {}) }}
          >
            <Text style={{ color: rating === 'down' ? colors.accent : colors.muted }}>{text(locale, 'notHelpful')}</Text>
          </Pressable>
        </View>}
      </View>
    })}
  </ScrollView>
}
