import type { ReactNode } from 'react'
import { Text, View, type ViewStyle } from 'react-native'
import type { NativeChatFile } from '@superstep/sdk/chat'
import { Composer } from './composer.js'
import type { ChatLocale } from './labels.js'
import { MessageList } from './message-list.js'
import { QuestionCard } from './question-card.js'
import { themeOf, type ChatTheme } from './theme.js'
import { useChat, type UseChatOptions } from './use-chat.js'

export interface ChatProps extends UseChatOptions {
  theme?: Partial<ChatTheme>
  pickFile?: () => Promise<NativeChatFile | null>
  renderMarkdown?: (value: string) => ReactNode
  style?: ViewStyle
}

function errorText(error: unknown): string | null {
  if (!error) return null
  return error instanceof Error && error.message ? error.message : null
}

export function Chat({ theme, pickFile, renderMarkdown, style, locale, ...options }: ChatProps) {
  const chat = useChat({ ...options, locale })
  const colors = themeOf(theme)
  const message = errorText(chat.error)
  return <View style={[{ flex: 1, backgroundColor: colors.background }, style]}>
    <MessageList chat={chat} locale={locale} theme={colors} renderMarkdown={renderMarkdown} />
    {message && <Text accessibilityRole="alert" style={{ color: colors.danger, paddingHorizontal: 12 }}>{message}</Text>}
    <QuestionCard chat={chat} locale={locale} theme={colors} />
    <Composer chat={chat} locale={locale} theme={colors} pickFile={pickFile} />
  </View>
}
