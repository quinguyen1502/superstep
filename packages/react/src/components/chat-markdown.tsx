/** A chat answer as Markdown (TASK-0085), styled by shadcn/typeset (`typeset typeset-chat`), with fenced code routed to
 *  the shadcn Code Block as the Message pattern says. Sanitised: no raw HTML (react-markdown escapes it, `skipHtml`),
 *  only http(s)/mailto/in-page/relative links (opened in a new tab without the opener), no remote images. */
import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { CodeBlock, CodeBlockActions, CodeBlockContent, CodeBlockCopyButton, CodeBlockHeader, CodeBlockLine, CodeBlockTitle } from '../ui/code-block.js'
import { useHighlightedCode } from '../hooks/use-highlighted-code.js'
import { safeUrl } from '../lib/chat.js'

function Code({ value, language }: { value: string; language: string }) {
  const lines = useHighlightedCode(value, language || 'text')
  return <CodeBlock size="sm" className="not-typeset" data-testid="chat-code">
    <CodeBlockHeader><CodeBlockTitle>{language || 'text'}</CodeBlockTitle><CodeBlockActions><CodeBlockCopyButton value={value} /></CodeBlockActions></CodeBlockHeader>
    <CodeBlockContent lineNumbers>{lines.map((l, i) => <CodeBlockLine key={i}>{l}</CodeBlockLine>)}</CodeBlockContent>
  </CodeBlock>
}

const components: Components = {
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children }) => {
    const lang = /language-([\w-]+)/.exec(className || '')?.[1]; const text = String(children ?? '')
    return lang || text.includes('\n') ? <Code value={text.replace(/\n$/, '')} language={lang ?? ''} /> : <code>{children}</code>
  },
  a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer nofollow">{children}</a>,
  img: ({ alt }) => <span>[{alt}]</span>,   // no remote images in a chat answer
  table: ({ children }) => <div className="typeset-scroll"><table>{children}</table></div>,
}

export function ChatMarkdown({ text }: { text: string }) {
  return <div className="typeset typeset-chat" data-testid="chat-markdown">
    <Markdown remarkPlugins={[remarkGfm]} skipHtml urlTransform={safeUrl} components={components}>{text}</Markdown></div>
}
