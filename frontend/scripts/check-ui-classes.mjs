#!/usr/bin/env node
// Alignment guardrail (docs/ui-conventions.md, rule 11): warns when className on a shadcn
// component imported from @/components/ui/* hand-sets a height, vertical padding, leading-none
// or an arbitrary text size (and size-* on a Button: use the icon-* sizes). Use the component's size prop or add a cva variant instead.
// Opt out on the element (same line or the line above): `ui-class-ok: <reason>`.
// Usage: node scripts/check-ui-classes.mjs [--strict] [files...]   (--strict exits 1 on hits)
import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const ROOT = path.resolve(import.meta.dirname, '../src')
const BANNED = /(?<![\w-])(?:[a-z0-9-]+:)*(h-\d[\w./]*|py-\d[\w./]*|leading-none|text-\[[^\]]+\])/g
// A Button sized by hand instead of size="icon-xs|icon-sm|icon|icon-lg"
const BUTTON_SIZE = /(?<![\w-])size-\d[\w./]*/g
const OPT_OUT = /ui-class-ok:[ \t]*[A-Za-z0-9]/
// Components whose size IS their content (placeholder boxes, scroll viewports, dividers): sizing them by className is the shadcn usage.
const DIMENSION = new Set(['Skeleton', 'ScrollArea', 'Separator', 'ResizablePanel'])

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) { if (e.name !== 'ui' && e.name !== '__tests__') walk(p, out) }
    else if (p.endsWith('.tsx')) out.push(p)
  }
  return out
}

function strings(node, acc = []) {
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) acc.push(node.text)
  else if (ts.isTemplateExpression(node)) { acc.push(node.head.text); node.templateSpans.forEach(s => { strings(s.expression, acc); acc.push(s.literal.text) }) }
  else ts.forEachChild(node, c => { strings(c, acc) })
  return acc
}

export function check(file, src = fs.readFileSync(file, 'utf8')) {
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  const ui = new Set()
  for (const st of sf.statements)
    if (ts.isImportDeclaration(st) && /^(?:@\/components\/ui\/|@superstep\/react\/ui\/|\.\.\/ui\/)/.test(st.moduleSpecifier.text))
      st.importClause?.namedBindings?.elements?.forEach(e => ui.add(e.name.text))
  const lines = src.split('\n'), hits = []
  const visit = n => {
    if ((ts.isJsxOpeningElement(n) || ts.isJsxSelfClosingElement(n)) && ui.has(n.tagName.getText(sf)) && !DIMENSION.has(n.tagName.getText(sf))) {
      for (const a of n.attributes.properties) {
        if (!ts.isJsxAttribute(a) || a.name.getText(sf) !== 'className' || !a.initializer) continue
        const text = strings(a.initializer).join(' '), tag = n.tagName.getText(sf)
        const found = [...text.matchAll(BANNED), ...(tag === 'Button' ? text.matchAll(BUTTON_SIZE) : [])].map(m => m[0])
        if (!found.length) continue
        const elLine = sf.getLineAndCharacterOfPosition(n.getStart(sf)).line
        const attrLine = sf.getLineAndCharacterOfPosition(a.getStart(sf)).line
        const ctx = lines.slice(Math.max(0, elLine - 1), attrLine + 1).join('\n')
        if (OPT_OUT.test(ctx)) continue
        hits.push({ file: path.relative(path.resolve(ROOT, '..'), file), line: attrLine + 1, tag: n.tagName.getText(sf), classes: found })
      }
    }
    ts.forEachChild(n, visit)
  }
  visit(sf)
  return hits
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2), strict = args.includes('--strict')
  const files = args.filter(a => !a.startsWith('--')).map(f => path.resolve(f))
  const hits = (files.length ? files : [...walk(ROOT), ...walk(path.resolve(ROOT, '../../packages/react/src'))]).flatMap(f => check(f))
  for (const h of hits) console.log(`${h.file}:${h.line}  <${h.tag}> ${h.classes.join(' ')}  (use the size prop / a cva variant, or add "ui-class-ok: <reason>")`)
  console.log(hits.length ? `\n${hits.length} ui-class warning(s)` : 'ui-class check: no hits')
  process.exit(strict && hits.length ? 1 : 0)
}
