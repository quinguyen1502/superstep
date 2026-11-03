// @vitest-environment jsdom
import { StrictMode } from 'react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from '@testing-library/react'
import { Chat, ChatProvider, Composer, MessageList, QuestionCard, Rating, useChat } from '../src/index'
import type { ChatController } from '../src/index'
import { Wire, SID, holding, ok, recorded } from '../../../sdk/typescript/test/chat-harness'

beforeAll(() => {
  vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
  vi.stubGlobal('IntersectionObserver', class { observe() {} unobserve() {} disconnect() {} })
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.scrollTo = vi.fn()
  URL.createObjectURL = vi.fn(() => 'blob:preview')
  URL.revokeObjectURL = vi.fn()
})
afterEach(cleanup)
const options = (wire: Wire) => ({ slug: 'sdk-fixture', baseUrl: 'https://superstep.test', visitorToken: 'fixture-visitor-token', fetch: wire.fetch, WebSocket: wire.Socket })
const ready = async (result: { current: ChatController }) => waitFor(() => expect(result.current.loading).toBe(false))
function Harness({ wire, children, identityKey }: { wire: Wire; identityKey?: string; children: (chat: ChatController) => React.ReactNode }) {
  const chat = useChat({ ...options(wire), identityKey }); return <ChatProvider chat={chat}>{children(chat)}</ChatProvider>
}

describe('useChat SDK binding', () => {
  it('marks implicit sessions as embeds and aborts their creation before a stale identity can write', async () => {
    const wire = new Wire()
    let release!: (response: Response) => void
    wire.override = (url, init) => url.pathname.endsWith('/sessions') && init.method === 'POST' ? new Promise<Response>(resolve => { release = resolve }) : undefined
    const { result, unmount } = renderHook(() => useChat({ ...options(wire), embed: true }))
    await ready(result)
    let pending!: Promise<unknown>
    act(() => { pending = result.current.send('Hello').catch(error => error) })
    await waitFor(() => expect(release).toBeTypeOf('function'))
    const start = wire.calls.find(call => call.init.method === 'POST')!
    expect(JSON.parse(String(start.init.body))).toEqual({ embed: true })
    unmount(); await act(async () => {})
    expect(start.init.signal?.aborted).toBe(true)
    release(ok({ ...recorded.session, turns: undefined }))
    await pending
    expect(wire.writes).toBe(0)
  })
  it('survives StrictMode replay, rerenders and refreshed token callbacks without losing its store', async () => {
    const wire = new Wire(), token = vi.fn(async () => 'fixture-token')
    const { result, rerender } = renderHook(() => useChat({ ...options(wire), visitorToken: undefined, getToken: () => token() }), { wrapper: StrictMode })
    await ready(result)
    const resource = result.current.resourceKey
    await act(async () => { await result.current.send('Hello') })
    expect(result.current.turns).toHaveLength(2)
    rerender(); await ready(result)
    expect(result.current.resourceKey).toBe(resource)
    expect(wire.writes).toBe(1)
    expect(token).toHaveBeenCalled()
  })
  it('changes identity without retaining another person’s turns and cancels its active socket on unmount', async () => {
    const wire = new Wire([holding])
    const { result, rerender, unmount } = renderHook(({ identity }) => useChat({ ...options(wire), identityKey: identity }), { initialProps: { identity: 'lan' } })
    await ready(result)
    let pending!: Promise<unknown>
    act(() => { pending = result.current.send('Hold').catch(e => e) })
    await waitFor(() => expect(wire.writes).toBe(1))
    rerender({ identity: 'minh' }); await ready(result)
    expect(result.current.turns).toHaveLength(0)
    expect(result.current.sessionId).toBeNull()
    expect((await pending as Error).name).toBe('AbortError')
    expect(wire.sockets[0].listenerCount()).toBe(0)
    unmount(); await act(async () => {})
  })
  it('resets the draft resource when a host selects a different session prop', async () => {
    const wire = new Wire(); wire.saved = true
    const { result, rerender } = renderHook(({ sessionId }) => useChat({ ...options(wire), sessionId }), { initialProps: { sessionId: SID as string | null } })
    await ready(result); expect(result.current.turns).toHaveLength(2)
    const previous = result.current.resourceKey
    rerender({ sessionId: null }); await ready(result)
    expect(result.current.turns).toHaveLength(0)
    expect(result.current.sessionId).toBeNull()
    expect(result.current.resourceKey).not.toBe(previous)
  })
  it('restores history, loads another session and exposes translated-error codes', async () => {
    const wire = new Wire(); wire.saved = true
    wire.override = url => url.pathname.endsWith('/sessions') ? ok({ sessions: [recorded.session] }) : undefined
    const { result } = renderHook(() => useChat(options(wire)))
    await ready(result)
    expect(result.current.sessionId).toBe(SID)
    expect(result.current.turns).toHaveLength(2)
    await act(async () => { await result.current.start() })
    expect(result.current.turns).toHaveLength(0)
    wire.override = () => { throw new Error('offline') }
    await act(async () => { await result.current.refresh().catch(() => {}) })
    expect(result.current.error).toMatchObject({ code: 'CONNECTION_ERROR' })
  })
})

describe('public components', () => {
  it('isolates locale, messages and theme for two instances', async () => {
    const wire = new Wire()
    const view = render(<><Chat {...options(wire)} locale="en" theme={{ primary: 'var(--brand)', radius: 12, colorScheme: 'dark' }} messages={{ 'chat.placeholder': 'Ask our team' }} />
      <Chat {...options(wire)} locale="vi" /></>)
    await waitFor(() => expect(screen.getAllByRole('textbox')).toHaveLength(2))
    expect(screen.getByPlaceholderText('Ask our team')).toBeTruthy()
    expect(screen.getByRole('textbox', { name: 'Tin nhắn' })).toBeTruthy()
    const roots = view.container.querySelectorAll('.superstep-chat')
    expect((roots[0] as HTMLElement).style.getPropertyValue('--ss-primary')).toBe('var(--brand)')
    expect(roots[0].getAttribute('data-color-scheme')).toBe('dark')
    expect(roots[1].getAttribute('lang')).toBe('vi')
  })
  it('sends through the shared composer and requires exact file name before removal; cancel settles safely', async () => {
    const wire = new Wire()
    wire.override = url => url.pathname.endsWith('/sdk-fixture') ? ok({ title: 'Fixture', attachments: { enabled: true, kinds: ['document'], max_files: 2, max_mb: 1 } }) : undefined
    const view = render(<Harness wire={wire}>{() => <Composer />}</Harness>)
    await waitFor(() => expect(view.container.querySelector('input[type=file]')).toBeTruthy())
    const picker = view.container.querySelector('input[type=file]')!
    fireEvent.change(picker, { target: { files: [new File(['abc'], 'file.txt', { type: 'text/plain' })] } })
    await waitFor(() => expect(screen.getByTestId('chat-file').getAttribute('data-state')).toBe('done'))
    fireEvent.click(screen.getByTestId('chat-file-remove'))
    let dialog = screen.getByRole('alertdialog')
    expect(view.container.querySelector('.superstep-chat')?.contains(dialog)).toBe(true)
    expect((within(dialog).getByRole('button', { name: 'Delete' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(screen.getByTestId('chat-file')).toBeTruthy()
    fireEvent.click(screen.getByTestId('chat-file-remove')); dialog = screen.getByRole('alertdialog')
    fireEvent.change(within(dialog).getByRole('textbox'), { target: { value: 'file.txt' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(screen.queryByTestId('chat-file')).toBeNull())
    await waitFor(() => expect(wire.calls.some(c => c.init.method === 'DELETE')).toBe(true))
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hello' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(wire.writes).toBe(1))
  })
  it('submits Human fields without coercing blank optional numbers to zero or requiring true booleans', async () => {
    const wire = new Wire(), answer = vi.fn(async () => ({}))
    render(<Harness wire={wire}>{chat => <QuestionCard chat={{ ...chat, busy: false, waiting: true, answer: answer as ChatController['answer'], question: { type: 'question', v: 1, seq: 1, node: 'human', prompt: 'Review', fields: [{ name: 'note', label: 'Note', required: true }, { name: 'optional', label: 'Optional', type: 'number' }, { name: 'approved', label: 'Approved', type: 'boolean', required: true }] } }} />}</Harness>)
    fireEvent.change(screen.getByLabelText('Note'), { target: { value: 'Checked' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send answer' }))
    await waitFor(() => expect(answer).toHaveBeenCalledWith({ note: 'Checked', approved: false }))
  })
  it('shows the live reply while a Human answer runs without a new visitor message', () => {
    const wire = new Wire()
    render(<Harness wire={wire}>{chat => <MessageList chat={{ ...chat, loading: false, busy: true, status: 'streaming', text: 'Working on your answer', pending: null, turns: [{ id: 'question', role: 'assistant', status: 'waiting', text: 'Review this', created: 1 }] }} />}</Harness>)
    expect(screen.getByText('Working on your answer')).toBeTruthy()
    expect(screen.queryByTestId('chat-mine')).toBeNull()
  })
  it('disables submission while a session is loading', () => {
    const wire = new Wire()
    render(<Harness wire={wire}>{chat => <Composer chat={{ ...chat, loading: false, status: 'loading', busy: true }} />}</Harness>)
    expect((screen.getByRole('textbox') as HTMLTextAreaElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Send' }) as HTMLButtonElement).disabled).toBe(true)
  })
  it('closes a destructive dialog when the person changes', async () => {
    const wire = new Wire()
    const contents = (chat: ChatController) => <Rating chat={{ ...chat, busy: false }} turn={{ id: 'old-turn', role: 'assistant', text: 'Done', created: 1, rating: { value: 'up', comment: '', updated: 1 } }} />
    const view = render(<Harness wire={wire} identityKey="lan">{contents}</Harness>)
    fireEvent.click(screen.getByTestId('chat-rate-up')); expect(screen.getByRole('alertdialog')).toBeTruthy()
    view.rerender(<Harness wire={wire} identityKey="minh">{contents}</Harness>)
    await waitFor(() => expect(screen.queryByRole('alertdialog')).toBeNull())
    expect(wire.calls.some(c => c.init.method === 'DELETE')).toBe(false)
  })
  it('requires the rating name before deleting feedback', async () => {
    const wire = new Wire(), rate = vi.fn(async () => {})
    render(<Harness wire={wire}>{chat => <Rating chat={{ ...chat, busy: false, rate }} turn={{ id: 'reply', role: 'assistant', text: 'Done', created: 1, status: 'ok', rating: { value: 'up', comment: '', updated: 1 } }} />}</Harness>)
    fireEvent.click(screen.getByTestId('chat-rate-up'))
    const dialog = screen.getByRole('alertdialog'), button = within(dialog).getByRole('button', { name: 'Delete' }) as HTMLButtonElement
    expect(button.disabled).toBe(true)
    fireEvent.change(within(dialog).getByRole('textbox'), { target: { value: 'Rating' } })
    fireEvent.click(button)
    await waitFor(() => expect(rate).toHaveBeenCalledWith('reply', null))
  })
})
