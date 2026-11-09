/** Chat triggers ( to ): types and the sample message the dialog shows. */

export type ChatTrigger = { id: string; name: string; channel_id: string; kind: string | null; channel_name: string | null; place: string
  event?: EventPolicy | null
  command: string; input_field: string; reply_field: string; enabled: boolean; note: string | null; last_message: number | null
  last_run_id: string | null; created: number }

export type EventPolicy = { senders: string[]; type: string; mapping: Record<string, string> }
export type ChatTriggerForm = { name: string; channel_id: string; place: string; command: string; input_field: string; reply_field: string; event?: EventPolicy | null }

export const newEventPolicy = (field = ''): EventPolicy => ({ senders: [], type: 'message.text', mapping: field ? { [field]: 'data.text' } : {} })

export const DM = 'dm'

/** Command words as the server stores them: lower case, one word, no leading "/". */
export const normCommand = (s: string) => s.trim().replace(/^\/+/, '').toLowerCase()
export const validCommand = (s: string) => /^[a-z0-9][a-z0-9_-]{0,31}$/.test(normCommand(s))

/** What someone types to start the run: a mention in a Slack channel, a command in a Telegram group, the word in a direct message. */
export function sampleMessage(kind: string | null, place: string, command: string, bot: string, text: string) {
  const word = normCommand(command) || '…'
  if (place === DM) return `${word} ${text}`
  return kind === 'telegram' ? `/${word} ${text}` : `@${bot} ${word} ${text}`
}
