import { Linking, Platform, Text, View, type TextStyle } from 'react-native'
import type { ChatTheme } from './theme.js'

export type Inline =
  | { kind: 'text'; text: string }
  | { kind: 'code'; text: string }
  | { kind: 'bold'; children: Inline[] }
  | { kind: 'italic'; children: Inline[] }
  | { kind: 'link'; text: string; href: string }

export type Block =
  | { kind: 'paragraph'; children: Inline[] }
  | { kind: 'list'; ordered: boolean; items: Inline[][] }

const SAFE_LINK = /^https?:\/\/[^\s]+$/

/** Paragraphs, bold, italic, code, http(s) links and lists. Anything else stays text. */
export function parseMarkdown(source: string): Block[] {
  const lines = source.replace(/\r\n/g, '\n').split('\n')
  const blocks: Block[] = []
  let paragraph: string[] = []
  let list: { ordered: boolean; items: string[] } | null = null
  const flushParagraph = () => {
    const text = paragraph.join(' ').trim()
    paragraph = []
    if (text) blocks.push({ kind: 'paragraph', children: parseInline(text) })
  }
  const flushList = () => {
    if (!list) return
    blocks.push({ kind: 'list', ordered: list.ordered, items: list.items.map(item => parseInline(item)) })
    list = null
  }
  for (const line of lines) {
    const item = /^(\s*)([-*]|\d+\.)\s+(.+)$/.exec(line)
    if (item) {
      flushParagraph()
      const ordered = /\d/.test(item[2] ?? '')
      if (!list || list.ordered !== ordered) {
        flushList()
        list = { ordered, items: [] }
      }
      list.items.push(item[3] ?? '')
      continue
    }
    if (!line.trim()) {
      flushParagraph()
      flushList()
      continue
    }
    flushList()
    paragraph.push(line.trim())
  }
  flushParagraph()
  flushList()
  return blocks
}

export function parseInline(source: string): Inline[] {
  const out: Inline[] = []
  let index = 0
  let buffer = ''
  const flush = () => {
    if (buffer) {
      out.push({ kind: 'text', text: buffer })
      buffer = ''
    }
  }
  while (index < source.length) {
    if (source[index] === '`') {
      const end = source.indexOf('`', index + 1)
      if (end > index + 1) {
        flush()
        out.push({ kind: 'code', text: source.slice(index + 1, end) })
        index = end + 1
        continue
      }
    }
    if (source.startsWith('**', index)) {
      const end = source.indexOf('**', index + 2)
      if (end > index + 2) {
        flush()
        out.push({ kind: 'bold', children: parseInline(source.slice(index + 2, end)) })
        index = end + 2
        continue
      }
    }
    if (source[index] === '*' || source[index] === '_') {
      const mark = source[index]!
      const end = source.indexOf(mark, index + 1)
      if (end > index + 1) {
        flush()
        out.push({ kind: 'italic', children: parseInline(source.slice(index + 1, end)) })
        index = end + 1
        continue
      }
    }
    if (source[index] === '[') {
      const close = source.indexOf(']', index + 1)
      if (close > index + 1 && source[close + 1] === '(') {
        const end = source.indexOf(')', close + 2)
        const href = end > close + 2 ? source.slice(close + 2, end) : ''
        if (SAFE_LINK.test(href)) {
          flush()
          out.push({ kind: 'link', text: source.slice(index + 1, close), href })
          index = end + 1
          continue
        }
      }
    }
    buffer += source[index]
    index += 1
  }
  flush()
  return out
}

const codeFont = Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' })

function InlineRun({ nodes, theme, base }: { nodes: Inline[]; theme: ChatTheme; base: TextStyle }) {
  return nodes.map((node, index) => {
    if (node.kind === 'text') return <Text key={index} style={base}>{node.text}</Text>
    if (node.kind === 'code') return <Text key={index} style={[base, { fontFamily: codeFont, backgroundColor: theme.code }]}>{node.text}</Text>
    if (node.kind === 'bold') return <Text key={index} style={[base, { fontWeight: '700' }]}><InlineRun nodes={node.children} theme={theme} base={base} /></Text>
    if (node.kind === 'italic') return <Text key={index} style={[base, { fontStyle: 'italic' }]}><InlineRun nodes={node.children} theme={theme} base={base} /></Text>
    return <Text
      key={index}
      style={[base, { color: theme.accent, textDecorationLine: 'underline' }]}
      accessibilityRole="link"
      onPress={() => { if (SAFE_LINK.test(node.href)) void Linking.openURL(node.href) }}
    >{node.text}</Text>
  })
}

export function MarkdownText({ text, theme }: { text: string; theme: ChatTheme }) {
  const base: TextStyle = { color: theme.assistantText, fontSize: theme.fontSize }
  const blocks = parseMarkdown(text)
  if (!blocks.length) return <Text style={base}>{text}</Text>
  return <View>
    {blocks.map((block, index) => block.kind === 'paragraph'
      ? <Text key={index} style={base}><InlineRun nodes={block.children} theme={theme} base={base} /></Text>
      : <View key={index}>
          {block.items.map((item, itemIndex) => <Text key={itemIndex} style={base}>
            {block.ordered ? `${itemIndex + 1}. ` : '- '}
            <InlineRun nodes={item} theme={theme} base={base} />
          </Text>)}
        </View>)}
  </View>
}
