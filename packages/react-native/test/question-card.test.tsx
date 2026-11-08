import { fireEvent, render } from '@testing-library/react-native'
import type { ChatQuestion } from '@superstep/sdk/chat'
import { QuestionCard } from '../src/question-card'

function question(extra: Partial<ChatQuestion>): ChatQuestion {
  return { type: 'question', v: 1, seq: 1, ...extra }
}

function card(extra: Partial<ChatQuestion>, answer = jest.fn(async () => undefined)) {
  const view = render(<QuestionCard locale="en" chat={{ question: question(extra), waiting: true, busy: false, answer }} />)
  return { ...view, answer }
}

describe('QuestionCard', () => {
  test('sends trimmed text', () => {
    const view = card({ prompt: 'Say hello', kind: 'text' })
    fireEvent.changeText(view.getByLabelText('Your answer'), '  Ada  ')
    fireEvent.press(view.getByRole('button', { name: 'Answer' }))
    expect(view.answer).toHaveBeenCalledWith('Ada')
  })

  test('sends a form object and drops prototype names', () => {
    const view = card({
      kind: 'form',
      fields: [
        { name: 'name', label: 'Name', type: 'text', required: true },
        { name: 'age', label: 'Age', type: 'number' },
        { name: 'ok', label: 'Agree', type: 'checkbox' },
        { name: '__proto__', label: 'Blocked', type: 'text' },
      ],
    })
    expect(view.queryByLabelText('Blocked')).toBeNull()
    fireEvent.changeText(view.getByLabelText('Name'), 'Ada')
    fireEvent.changeText(view.getByLabelText('Age'), '4')
    fireEvent(view.getByLabelText('Agree'), 'valueChange', true)
    fireEvent.press(view.getByRole('button', { name: 'Answer' }))
    expect(view.answer).toHaveBeenCalledWith({ name: 'Ada', age: 4, ok: true })
  })

  test('sends a choice and an approval', () => {
    const choices = card({ options: ['Red', 'Blue'] })
    fireEvent.press(choices.getByRole('button', { name: 'Blue' }))
    expect(choices.answer).toHaveBeenCalledWith('Blue')
    const approval = card({ kind: 'approval', prompt: 'Ship it?' })
    fireEvent.press(approval.getByRole('button', { name: 'Approve' }))
    expect(approval.answer).toHaveBeenCalledWith('approved')
  })

  test('shows the reviewer wait in Vietnamese', () => {
    const view = render(<QuestionCard locale="vi" chat={{ question: question({ prompt: 'Wait' }), waiting: true, busy: false, answeredBy: 'reviewer', answer: jest.fn() }} />)
    expect(view.getByText('Đang chờ người duyệt')).toBeTruthy()
  })
})
