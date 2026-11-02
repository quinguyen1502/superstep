import type { components } from '../schema.js'
import type { ServerFrame } from './frames.js'

type Schemas = components['schemas']
export type ChatPage = Schemas['ChatPage']
export type ChatSession = Schemas['ChatSession']
export type ChatSessionView = Schemas['ChatSessionView']
export type ChatTurn = Schemas['ChatTurn']
export type ChatAttachment = Schemas['ChatAttachment']
export type ChatRating = Schemas['ChatRating']
export type ChatSessionList = Schemas['ChatSessionList']
export type ChatTurns = Schemas['ChatTurns']
export type ChatQuestion = Extract<ServerFrame, { type: 'question' }>
export type ChatStatus = Extract<ServerFrame, { type: 'done' }>['status']

/** The browser, React Native, and Node socket adapters need only this surface. */
export interface WebSocketLike {
  readonly readyState: number
  send(data: string): void
  close(code?: number, reason?: string): void
  addEventListener(type: string, listener: (event: any) => void): void
  removeEventListener(type: string, listener: (event: any) => void): void
}
export type WebSocketConstructor = new (url: string) => WebSocketLike
export interface ChatOptions {
  /** A short-lived user token from your application's backend. Called for each operation and once more on expiry. */
  getToken?: () => string | Promise<string>
  /** Anonymous identity, saved by the host; never mixed with getToken. */
  visitorToken?: string
  onVisitorToken?: (token: string) => void
  fetch?: typeof fetch
  WebSocket?: WebSocketConstructor
  FormData?: typeof FormData
  Blob?: typeof Blob
}
export interface ChatClientOptions extends ChatOptions { baseUrl: string }
export interface ChatRequestOptions { signal?: AbortSignal }
export interface ChatStreamOptions extends ChatRequestOptions {
  locale?: 'en' | 'vi'
  /** History cursor already held by the caller. It never causes a message to be resent. */
  after?: string
  /** Overall socket deadline in ms; default 300000. null disables it. */
  timeoutMs?: number | null
  /** Bounded history checks after completion/interruption; default 20, at most 100. */
  recoveryAttempts?: number
  recoveryIntervalMs?: number
}
export interface ChatSendOptions extends ChatStreamOptions { attachments?: string[] }
export interface ChatAnswerOptions extends ChatStreamOptions { node?: string }
export type NativeChatFile = { uri: string; name: string; type: string }
export type ChatFile = Blob | Uint8Array | ArrayBuffer | NativeChatFile
export interface ChatUploadOptions extends ChatRequestOptions { name?: string; type?: string }
export interface ChatResult {
  sessionId: string
  runId?: string
  turnId?: string
  status: ChatStatus
  text: string
  turns: ChatTurn[]
  question?: ChatQuestion
  recovered: boolean
}
export type ChatEvent = ServerFrame | { type: 'history'; turns: ChatTurn[] } | { type: 'result'; result: ChatResult }
export type { ClientFrame, ServerFrame } from './frames.js'
