import { afterAll, describe, expect, it } from 'vitest'
import i18n, { eventErrors, issueTexts } from '../i18n'

// TASK-0132: validation messages are shown in the UI language by their code, else as the server's English text.
describe('issueTexts', () => {
  afterAll(() => i18n.changeLanguage('en'))

  it('translates known codes with their parameters and keeps the rest', async () => {
    await i18n.changeLanguage('vi')
    const errors = ['Retriever node r1: choose a knowledge base', 'Node c: SyntaxError', 'old server text']
    const issues = [{ code: 'RETRIEVER_KB_MISSING', params: { node: 'r1' } }, { code: 'NO_SUCH_CODE' }, null]
    expect(issueTexts(errors, issues)).toEqual(['Node Retriever r1: hãy chọn kho tri thức', 'Node c: SyntaxError', 'old server text'])
    expect(issueTexts(errors)).toEqual(errors)
  })

  it('translates the codes of a run error event', async () => {
    await i18n.changeLanguage('vi')
    const ev = { error: { code: 'WORKFLOW_INVALID', message: 'Workflow is invalid' }, errors: ['At least one End node is required'],
      issues: [{ code: 'END_MISSING', params: {} }] }
    expect(eventErrors(ev)).toEqual(['Cần ít nhất một node End'])
  })
})
