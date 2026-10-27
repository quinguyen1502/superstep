/** Locale checks (TASK-0078): en and vi have the same keys and placeholders, vi uses the glossary in
 * docs/ui-conventions.md, and any vi string left identical to en is on the reviewed allowlist below. */
import { describe, expect, it } from 'vitest'
import en from '../../locales/en.json'
import vi from '../../locales/vi.json'

type Tree = { [k: string]: string | Tree }
const flat = (t: Tree, p = ''): Record<string, string> =>
  Object.entries(t).reduce<Record<string, string>>((o, [k, v]) =>
    typeof v === 'string' ? { ...o, [p + k]: v } : { ...o, ...flat(v, `${p}${k}.`) }, {})
const EN = flat(en as Tree)
const VI = flat(vi as Tree)
const vars = (s: string) => [...s.matchAll(/{{\s*([\w.]+)\s*}}/g)].map((m) => m[1]).sort()

/** vi strings that may stay identical to en: brand names, IDs, examples, and glossary terms kept in English. */
const SAME_OK = new Set([
  'activity.types.workflow',
  'agent.workflow',
  'chat.page.title',
  'chat.embed.iframe',
  'chat.publish.logo',
  'langsmith.title',
  'tests.langsmith',
  'api.button',
  'mcpServer.tab', 'mcpServer.clients.cursor', 'mcpServer.clients.claude-desktop', 'mcpServer.clients.claude-code', 'mcpServer.where.cursor',  // product names, a file name
  'timeTravel.state',
  'approvals.col.run',
  'approvals.field.access_token',
  'approvals.field.app_secret',
  'approvals.field.bot_token',
  'approvals.field.phone_number_id',
  'approvals.field.signing_secret',
  'approvals.field.verify_token',
  'approvals.field.webhook_secret',
  'approvals.identity.slack',
  'approvals.identity.telegram',
  'approvals.identityPh.slack',
  'approvals.identityPh.telegram',
  'chat.settings.enabled',
  'chat.step.input',
  'chat.step.output',
  'chat.tab',
  'editor.mobileNav.canvas',  // glossary: canvas stays in English
  'approvals.identityPh.whatsapp',
  'approvals.kind.slack',
  'approvals.kind.studio',
  'approvals.kind.teams',
  'approvals.kind.telegram',
  'approvals.kind.whatsapp',
  'approvals.node.target.slack',
  'approvals.node.target.telegram',
  'approvals.node.targetPh.email',
  'approvals.node.targetPh.slack',
  'approvals.node.targetPh.teams',
  'approvals.node.targetPh.telegram',
  'approvals.node.targetPh.whatsapp',
  'approve.workflow',
  'auth.email',
  'auth.loginHint',
  'chatTriggers.badge',
  'chatTriggers.bot',
  'code.adminImage',
  'code.adminRuntime',
  'code.languages.python',
  'code.languages.typescript',
  'code.runtimeLabel',
  'code.traceback',
  'codeView.tab',
  'codeView.version',
  'creds.anthropic',
  'creds.button',
  'creds.key',
  'creds.providers.anthropic',
  'creds.providers.openrouter',
  'creds.smtp.fromNamePh',
  'creds.smtp.presets.gmail',
  'creds.smtp.presets.mailgun',
  'creds.smtp.presets.outlook',
  'creds.smtp.presets.resend',
  'creds.smtp.presets.sendgrid',
  'creds.smtp.securityOpts.ssl',
  'creds.smtp.securityOpts.starttls',
  'creds.title',
  'creds.titlePh',
  'decision.id',
  'decision.model',
  'editor.codeMode',
  'editor.idBadge',
  'editor.jsonTitle',
  'editor.llmMode',
  'editor.reducer',
  'editor.stateSchema',
  'editor.tabInput',
  'email.bcc',
  'email.cc',
  'email.formats.html',
  'errors.TEST_CASE_INVALID',
  'field.bodyTemplate',
  'field.code',
  'field.method',
  'field.model',
  'field.promptTemplate',
  'field.url',
  'human.node',
  'import.button',
  'import.start',
  'import.title',
  'import.url',
  'lang.en',
  'lang.vi',
  'list.colNodes',
  'list.title',
  'mcp.http',
  'share.email',
  'shortcuts.groups.canvas',
  'status.ok',
  'templates.builtin.builtin-chatbot.name',
  'templates.tests_one',
  'tests.badge',
  'tests.desc.field',
  'tests.desc.fieldNoValue',
  'tests.input',
  'tests.kinds.node',
  'tests.node',
  'trace.diff',
  'trace.input',
  'trace.output',
  'trace.tokensShort',
  'transfer.kinds.credential',
  'transfer.kinds.subgraph',
  'users.email',
  'validation.NODE_PROBLEM',
  'versions.nodes_one',
  'versions.stateTitle',
])

/** Terms the glossary replaces: [pattern, why]. */
const BANNED: [RegExp, string][] = [
  [/X[óò]a|x[óò]a|h[óò]a\b|[hH]ủy|tùy/, 'old-style diacritics: use xoá, mã hoá, huỷ'],
  [/[Ee]-mail/, 'use “email”'],
  [/thông tin xác thực/i, 'use “credential”'],
  [/lượt chạy|lần chạy/i, 'use “run”'],
  [/cơ sở tri thức/i, 'use “kho tri thức”'],
  [/phê duyệt/i, 'use “duyệt”'],
  [/không bắt buộc/i, 'use “tuỳ chọn”'],
  [/\d+\}\} nút|\bnút node\b/, '“nút” means a button; nodes are “node”'],
  [/\b[Ff]ields?\b/, 'use “trường”'],
  [/\bProvider\b/, 'use “nhà cung cấp”'],
  [/^(Nút|Cạnh)$/, 'nodes and edges stay “node” / “edge”'],
]

describe('locales', () => {
  it('en and vi have the same keys', () => {
    expect(Object.keys(VI).sort()).toEqual(Object.keys(EN).sort())
  })
  it('placeholders match', () => {
    const bad = Object.keys(EN).filter((k) => k in VI && vars(EN[k]).join() !== vars(VI[k]).join())
    expect(bad).toEqual([])
  })
  it('the subprocess-runtime badge reads "Runs on host" with a tooltip (glossary)', () => {
    expect([EN['code.notIsolatedShort'], EN['code.notIsolatedNode']]).toEqual(['Runs on host', 'Runs on host'])
    expect([VI['code.notIsolatedShort'], VI['code.notIsolatedNode']]).toEqual(['Chạy trực tiếp trên server', 'Chạy trên server'])
    expect(EN['code.notIsolatedTip']).toBe('Code runs directly on the server, without Docker limiting its access. Use only for trusted code.')
    expect(VI['code.notIsolatedTip']).toBe('Code đang chạy trực tiếp trên máy chủ, không có Docker giới hạn quyền. Chỉ nên dùng cho code tin cậy.')
    expect(Object.entries(EN).filter(([, v]) => /not isolated|without isolation|unisolated/i.test(v)).map(([k]) => k)).toEqual([])
    expect(Object.entries(VI).filter(([, v]) => /không cách ly/i.test(v)).map(([k]) => k)).toEqual([])
  })
  it('vi follows the glossary', () => {
    const bad = Object.entries(VI).flatMap(([k, v]) =>
      BANNED.filter(([re]) => re.test(v.replace(/{{[^}]*}}/g, ''))).map(([, why]) => `${k}: ${why}`))
    expect(bad).toEqual([])
  })
  it('vi strings identical to en are reviewed', () => {
    const bad = Object.keys(EN).filter((k) => VI[k] === EN[k] && EN[k] !== '' && !SAME_OK.has(k))
    expect(bad).toEqual([])
  })
})
