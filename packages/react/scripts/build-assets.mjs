import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { compile } from '@tailwindcss/node'
import { Scanner } from '@tailwindcss/oxide'
import postcss from 'postcss'
import selectors from 'postcss-selector-parser'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const pkg = path.join(root, 'packages/react')
const write = (file, text) => fs.writeFile(path.join(pkg, file), text)
await fs.mkdir(path.join(pkg, 'dist'), { recursive: true })
const languages = {}
for (const lang of ['en', 'vi']) {
  const source = JSON.parse(await fs.readFile(path.join(root, `frontend/src/locales/${lang}.json`), 'utf8'))
  languages[lang] = { chat: source.chat, confirmDelete: source.confirmDelete, human: { approve: source.human.approve, reject: source.human.reject },
    errors: Object.fromEntries(Object.entries(source.errors).filter(([key]) => /^(CHAT_|AUTH_|HTTP_)/.test(key) || ['NETWORK_ERROR', 'VALIDATION_ERROR', 'INTERNAL_ERROR'].includes(key))) }
}
await write('src/public/messages.generated.ts', '// Generated from frontend locales; edit the source dictionaries, never this file.\nexport const messages = '+JSON.stringify(languages)+' as const\n')
await fs.mkdir(path.join(root, 'examples/react-chat/src'), { recursive: true })
await fs.writeFile(path.join(root, 'examples/react-chat/src/messages.generated.ts'), '// Generated from frontend locales.\nexport const messages = '+JSON.stringify(Object.fromEntries(Object.entries(languages).map(([lang,value])=>[lang,value.chat.toolkit])))+' as const\n')
const source = postcss.parse(await fs.readFile(path.join(root, 'frontend/src/index.css'), 'utf8'))
const palette = source.nodes.find(n=>n.type==='rule' && n.selector===':root').nodes.filter(n=>n.type==='decl' && ['--primary','--primary-foreground','--popover','--ring','--radius'].includes(n.prop))
const widgetTokens = Object.fromEntries(palette.map(n=>[n.prop.replace('--','--ss-widget-'),n.value]))
widgetTokens['--ss-widget-shadow'] = '0 12px 32px color-mix(in oklch, '+widgetTokens['--ss-widget-primary']+', transparent 76%)'
await fs.writeFile(path.join(root, 'frontend/src/widget/assets.generated.ts'), '// Generated from canonical locales/theme; no independent widget palette.\nexport const labels = '+JSON.stringify(Object.fromEntries(Object.entries(languages).map(([lang,value])=>[lang,value.chat.widget])))+' as const\nexport const tokens = '+JSON.stringify(widgetTokens)+' as const\n')
const theme = source.nodes.filter(n => n.type === 'atrule' && (n.name === 'theme' || n.name === 'utility' || (n.name === 'layer' && n.params === 'base'))).map(n => n.toString()).join('\n')
const scanner = new Scanner({ sources: [{ base: path.join(pkg, 'src'), pattern: '**/*.{ts,tsx}', negated: false }, { base: path.join(pkg, 'src'), pattern: '**/messages.generated.ts', negated: true }] })
const candidate = scanner.scan()
const compiler = await compile('@import "tailwindcss";\n@import "tw-animate-css";\n@import "shadcn/tailwind.css";\n@custom-variant dark (&:where(.superstep-chat[data-color-scheme="dark"], .superstep-chat[data-color-scheme="dark"] *));\n'+theme, { base: path.join(root, 'frontend'), onDependency() {} })
const css = postcss.parse(compiler.build(candidate)+'\n'+await fs.readFile(path.join(root, 'frontend/src/typeset.css'), 'utf8'))
const scopedVariable = value => value.replace(/--([a-zA-Z_][\w-]*)/g, (all, name) => /^(ss-|radix-|shiki-)/.test(name) ? all : '--ss-'+name)
const frames = new Set()
css.walkAtRules('keyframes', a => { frames.add(a.params); a.params = 'ss-'+a.params })
css.walkAtRules('property', a => { a.params = scopedVariable(a.params) })
css.walkDecls(d => {
  if (d.prop.startsWith('--')) d.prop = scopedVariable(d.prop)
  d.value = scopedVariable(d.value)
  for (const name of frames) d.value = d.value.replace(new RegExp(`(^|[\\s,])${name}(?=$|[\\s,])`, 'g'), '$1ss-'+name)
})
const inFrames = node => { for (let p=node.parent;p;p=p.parent) if (p.type==='atrule' && /keyframes$/.test(p.name)) return true; return false }
const inRule = node => { for (let p=node.parent;p;p=p.parent) if (p.type==='rule') return true; return false }
css.walkRules(rule => {
  if (inFrames(rule) || inRule(rule)) return
  const parsed = selectors().astSync(rule.selector)
  const output = []
  for (const selector of parsed.nodes) {
    let rootRule = false
    selector.walk(n => {
      if ((n.type==='pseudo' && [':root', ':host'].includes(n.value)) || (n.type==='tag' && ['html','body'].includes(n.value))) { n.replaceWith(selectors.className({ value: 'superstep-chat' })); rootRule=true }
    })
    selector.walkClasses(n => { if (n.value === 'dark') n.replaceWith(selectors.attribute({ attribute: 'data-color-scheme', operator: '=', value: 'dark', quoteMark: '"' })) })
    const plain = selector.toString().trim()
    const prefix = rootRule ? '' : '.superstep-chat '
    output.push(prefix+plain)
    const renamed = selector.clone(); let changed=false
    renamed.walkClasses(n => { if (n.value !== 'superstep-chat' && !n.value.startsWith('ss-')) { n.value='ss-'+n.value; changed=true } })
    if (changed) output.push(prefix+renamed.toString().trim())
  }
  rule.selector=output.join(',\n')
})
// Layer names must not reorder a host application's cascade.
css.walkAtRules('layer', a => { if (a.nodes) a.replaceWith(...a.nodes); else a.remove() })
const defaults = []
for (const [input, target] of [[':root','.superstep-chat'],['.dark','.superstep-chat[data-color-scheme="dark"]']]) {
  const block=source.nodes.find(n => n.type==='rule' && n.selector===input)
  const declarations=block?.nodes.filter(n=>n.type==='decl' && !n.prop.startsWith('--node-') && !n.prop.startsWith('--sidebar-') && !n.prop.startsWith('--chart-')).map(n=>`${scopedVariable(n.prop)}:${scopedVariable(n.value)}`).join(';') ?? ''
  defaults.push(`${target}{${declarations}}`)
}
const base = `.superstep-chat{--ss-font:system-ui,sans-serif;--ss-font-sans:var(--ss-font);font-family:var(--ss-font);font-size:14px;line-height:1.5;color:var(--ss-foreground);background:var(--ss-background);color-scheme:light;min-width:0}.superstep-chat[data-color-scheme="dark"]{color-scheme:dark}.superstep-chat.ss-chat{display:flex;flex-direction:column;height:100%;min-height:20rem;overflow:hidden;border:1px solid var(--ss-border);border-radius:var(--ss-radius)}.superstep-chat .ss-error{color:var(--ss-destructive)}\n`
await write('dist/styles.css', '/* Prebuilt, scoped SDK CSS. Generated from the existing shadcn theme/UI, with ss-prefixed utility aliases. */\n'+css.toString()+'\n'+defaults.join('\n')+'\n'+base)
