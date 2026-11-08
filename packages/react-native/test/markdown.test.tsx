import { Linking } from 'react-native'
import { fireEvent, render } from '@testing-library/react-native'
import { MarkdownText, parseMarkdown } from '../src/markdown'
import { defaultTheme } from '../src/theme'

describe('safe markdown', () => {
  test('keeps the supported subset and leaves unsafe links as text', () => {
    const blocks = parseMarkdown('Hello **bold** and *italic* plus `code`.\n\n- one\n- [docs](https://example.com/docs)\n\n[bad](javascript:alert(1))')
    expect(blocks.map(block => block.kind)).toEqual(['paragraph', 'list', 'paragraph'])
    const paragraph = blocks[0]
    expect(paragraph && paragraph.kind === 'paragraph' && paragraph.children.map(node => node.kind)).toEqual(['text', 'bold', 'text', 'italic', 'text', 'code', 'text'])
    const list = blocks[1]
    expect(list && list.kind === 'list' && list.items[1]?.some(node => node.kind === 'link' && node.href === 'https://example.com/docs')).toBe(true)
    const unsafe = blocks[2]
    expect(unsafe && unsafe.kind === 'paragraph' && unsafe.children).toEqual([{ kind: 'text', text: '[bad](javascript:alert(1))' }])
  })

  test('opens only an http(s) link', () => {
    const open = jest.spyOn(Linking, 'openURL').mockResolvedValue(undefined as never)
    const view = render(<MarkdownText theme={defaultTheme} text={'See [docs](https://example.com/docs)'} />)
    fireEvent.press(view.getByRole('link', { name: 'docs' }))
    expect(open).toHaveBeenCalledWith('https://example.com/docs')
    open.mockRestore()
  })
})
