// Only scripts/sdk_integration.sh creates the isolated backend and ephemeral app keys used here.
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { AuthenticationError, NotFoundError, Superstep } from '../src/index'
import { mintChatToken } from '../src/server'
import type { ChatClient, ChatStream } from '../src/chat/index'

const baseUrl = process.env.SUPERSTEP_IT_BASE_URL, file = process.env.SUPERSTEP_IT_CHAT_CONFIG
const fixtures = file ? JSON.parse(readFileSync(file, 'utf8')) : undefined
const all = async (stream: ChatStream) => { for await (const _ of stream) { /* Drain bounded stream. */ } return stream.result }
type Key = { keyId: string; secret: string; slug: string }
const userChat = (key: Key, userId: string): ChatClient => new Superstep({ baseUrl }).chat(key.slug, { getToken: () => mintChatToken({ ...key, userId, name: 'SDK user' }) })

describe.skipIf(!baseUrl || !fixtures)('live chat SDK', () => {
  it('mints a backend-verified user token, streams a conversation, uploads bytes and rates a persisted answer', async () => {
    const chat = userChat(fixtures.chat, 'sdk-a')
    expect((await chat.info()).slug).toBe(fixtures.chat.slug)
    const session = await chat.start(), attachment = await chat.attachments.upload(session.id, Buffer.from('hello file'), { name: 'sdk.txt', type: 'text/plain' })
    expect(await (await chat.attachments.download(session.id, attachment.id)).text()).toBe('hello file')
    await chat.attachments.delete(session.id, attachment.id)
    const answer = await all(chat.send(session.id, 'Hello from the SDK', { recoveryIntervalMs: 25 }))
    expect(answer).toMatchObject({ status: 'ok', recovered: false }); expect(answer.turnId).toBeTruthy()
    expect(answer.text).toContain('Hello from the SDK')
    expect((await chat.get(session.id)).turns).toHaveLength(2)
    expect((await chat.list()).sessions.some(value => value.id === session.id)).toBe(true)
    expect((await chat.turns(session.id, { after: answer.turns[0].id })).turns[0].id).toBe(answer.turnId)
    expect(await chat.ratings.put(session.id, answer.turnId!, 'down', { comment: 'Integration test' })).toMatchObject({ value: 'down' })
    expect(await chat.ratings.delete(session.id, answer.turnId!)).toEqual({ ok: true })
    const secondUser = userChat(fixtures.chat, 'sdk-b')
    await expect(secondUser.get(session.id)).rejects.toBeInstanceOf(NotFoundError)
    expect((await secondUser.list()).sessions).toHaveLength(0)
  }, 30_000)

  for (const response of ['yes', { approved: true, note: 'Confirmed' }]) it(`answers a Human node with ${typeof response === 'string' ? 'text' : 'form values'}`, async () => {
    const chat = userChat(fixtures.human, 'sdk-human-' + typeof response), session = await chat.start()
    const question = await all(chat.send(session.id, 'approval', { recoveryIntervalMs: 25 }))
    expect(question.status).toBe('waiting'); expect(question.question?.node).toBe('ask')
    const answer = await all(chat.answer(session.id, response, { node: question.question!.node!, recoveryIntervalMs: 25 }))
    expect(answer.status).toBe('ok'); expect(answer.turnId).not.toBe(question.turnId)
    if (typeof response === 'object') expect(answer.text).toContain('approved')
    expect((await chat.get(session.id)).turns.some(turn => turn.role === 'user' && turn.text.includes(typeof response === 'string' ? response : 'approved: true'))).toBe(true)
  }, 30_000)

  it('persists an anonymous visitor token through host-controlled storage', async () => {
    let token: string | undefined
    const chat = new Superstep({ baseUrl }).chat(fixtures.chat.slug, { onVisitorToken: value => { token = value } }), session = await chat.start()
    expect(token).toBeTruthy()
    const restored = new Superstep({ baseUrl }).chat(fixtures.chat.slug, { visitorToken: token })
    expect((await restored.get(session.id)).id).toBe(session.id)
    expect((await all(restored.send(session.id, 'Anonymous SDK', { recoveryIntervalMs: 25 }))).status).toBe('ok')
  }, 30_000)

  it('refreshes an expired HTTP token once and observes immediate key revocation', async () => {
    // Use a separate key so test order never invalidates other cases.
    const headers = { Authorization: `Bearer ${fixtures.owner}`, 'Content-Type': 'application/json' }
    const response = await fetch(`${baseUrl}/api/workflows/${fixtures.chat.workflowId}/chat/app-keys`, { method: 'POST', headers, body: JSON.stringify({ label: 'SDK revoke' }) })
    const key = (await response.json()).data, options = { keyId: key.key_id, secret: key.secret, slug: fixtures.chat.slug, userId: 'sdk-refresh' }
    const current = await mintChatToken(options), dateNow = Date.now
    // Fixed older clock for a genuinely signed expired token; restore before any I/O.
    let expired: string
    try { Date.now = () => dateNow() - 7200_000; expired = await mintChatToken(options) } finally { Date.now = dateNow }
    let calls = 0
    const chat = new Superstep({ baseUrl }).chat(options.slug, { getToken: () => ++calls === 1 ? expired : current })
    await chat.list(); expect(calls).toBe(2)
    const revoked = await fetch(`${baseUrl}/api/workflows/${fixtures.chat.workflowId}/chat/app-keys/${key.key_id}`, { method: 'DELETE', headers })
    expect(revoked.ok).toBe(true)
    await expect(chat.list()).rejects.toBeInstanceOf(AuthenticationError)
    expect(calls).toBe(3)
  })
})
