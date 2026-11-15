import type { ClientFrame } from '@superstep/sdk/chat'
import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { Chat } from '../src/chat'
import { MessageList } from '../src/message-list'
import { text } from '../src/labels'
import { Harness, type FakeSocket } from './harness'

function frame(socket: FakeSocket | undefined, type: ClientFrame['type']) {
  return socket?.sent.find(item => item.type === type)
}

async function send(view: ReturnType<typeof render>, value: string) {
  fireEvent.changeText(view.getByLabelText('Message'), value)
  fireEvent.press(view.getByRole('button', { name: 'Send' }))
}

describe('Chat with a fake socket', () => {
  test('streams a reply from the socket', async () => {
    const harness = new Harness()
    const view = render(<Chat {...harness.props()} />)
    await send(view, 'Hi')
    expect(await view.findByText('Hello')).toBeTruthy()
    const message = harness.sockets[0]?.sent.find(frame => frame.type === 'message')
    expect(message).toMatchObject({ type: 'message', text: 'Hi', chat_session_id: 'sess-1' })
  })

  test('uses the token callback and uploads a picked file before send', async () => {
    const harness = new Harness()
    const getToken = jest.fn(async () => 'token-fixture')
    const view = render(<Chat
      slug="demo"
      baseUrl="https://studio.test"
      getToken={getToken}
      fetch={harness.fetch}
      WebSocket={harness.Socket}
      FormData={harness.FormData}
      pickFile={async () => ({ uri: 'file:///note.txt', name: 'note.txt', type: 'text/plain' })}
    />)
    fireEvent.press(view.getByRole('button', { name: 'Attach a file' }))
    expect(await view.findByText('note.txt')).toBeTruthy()
    await send(view, 'With file')
    await view.findByText('Hello')
    expect(getToken).toHaveBeenCalled()
    expect(harness.calls.some(call => call.authorization === 'Bearer token-fixture')).toBe(true)
    const message = frame(harness.sockets[harness.sockets.length - 1], 'message')
    expect(message).toMatchObject({ attachments: ['file-1'] })
  })

  test('answers a question frame from the socket', async () => {
    const harness = new Harness(true)
    const view = render(<Chat {...harness.props()} />)
    await send(view, 'Start')
    expect(await view.findByTestId('question-card')).toBeTruthy()
    fireEvent.changeText(view.getByLabelText('Your answer'), 'Ada')
    fireEvent.press(view.getByRole('button', { name: 'Answer' }))
    expect(await view.findByText('Hello')).toBeTruthy()
    const answer = frame(harness.sockets[harness.sockets.length - 1], 'answer')
    expect(answer).toMatchObject({ type: 'answer', response: 'Ada', node: 'ask' })
  })

  test('rates an assistant turn', async () => {
    const harness = new Harness()
    const view = render(<Chat {...harness.props()} />)
    await send(view, 'Hi')
    await view.findByText('Hello')
    fireEvent.press(view.getByRole('button', { name: 'Helpful' }))
    await waitFor(() => expect(harness.rating?.value).toBe('up'))
    expect(view.getByRole('button', { name: 'Helpful' }).props.accessibilityState).toMatchObject({ selected: true })
  })

  test('rates from a host-rendered list', async () => {
    const rate = jest.fn(async () => undefined)
    const view = render(<MessageList locale="vi" chat={{
      turns: [{ id: 't1', role: 'assistant', text: 'Xin chao', created: 1, inherited: false, editable: false, regeneratable: false }],
      text: '', status: 'idle', pending: null, rate,
    }} />)
    fireEvent.press(view.getByRole('button', { name: text('vi', 'helpful') }))
    expect(rate).toHaveBeenCalledWith('t1', 'up')
  })
})
