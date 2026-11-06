import { defineConfig } from '@playwright/test'
import os from 'os'
import path from 'path'

// Isolated stack: backend on 8100 (temp DB), Vite on 5190 proxying to it.
// Ports are overridable (E2E_API_PORT/E2E_UI_PORT/E2E_CHAT_PORT) so two worktrees can run the suite side by side.
const env = (k: string, d: number) => Number(process.env[k] || d)
const API = env('E2E_API_PORT', 8100), UI = env('E2E_UI_PORT', 5190), CHAT = env('E2E_CHAT_PORT', 8111)  // CHAT: fake Slack/Telegram APIs (backend/tests/fixtures/mock_chat_api.py)
const ATTACH_DIR = path.resolve('../backend/.e2e-attachments')  // the fs backend's folder in e2e (TASK-0195)
const SMTP = env('E2E_SMTP_PORT', 8125)  // local SMTP sink for Send email nodes (TASK-0051); specs read it as E2E_SMTP_PORT
const CHANNEL_SMTP = process.env.E2E_CHANNEL_SMTP === '1'  // opt-in system SMTP; ordinary session/notification specs expect it disabled
const DRIVE = process.env.E2E_DRIVE_FIXTURE === '1'  // fixed Google HTTP double; explicit opt-in only
const EXPENSE = process.env.E2E_EXPENSE_FIXTURE === '1'  // isolated paid-model/Google fixture, explicit opt-in only
if (DRIVE && EXPENSE) throw new Error('Run Drive and expense acceptance fixtures separately')
const ENTRYPOINT = EXPENSE ? 'tests.fixtures.expense_preview:app' : DRIVE ? 'tests.fixtures.drive_preview:app' : 'app.main:app'
process.env.E2E_SMTP_PORT = String(SMTP)
const db = path.join(os.tmpdir(), `lgs-e2e-${Date.now()}.db`)
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  workers: 1,
  reporter: [['list']],
  use: {
    locale: 'vi-VN', // existing specs assert Vietnamese UI text; i18n.spec.ts covers English + switching
    baseURL: `http://127.0.0.1:${UI}`,
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',  // with the trace, uploaded by the CI e2e job (TASK-0199)
    // Use a system Chrome when PW_CHROME is set (no browser download needed); otherwise Playwright's Chromium.
    launchOptions: process.env.PW_CHROME ? { executablePath: process.env.PW_CHROME } : {},
  },
  webServer: [
    { command: `python3 tests/fixtures/mock_chat_api.py ${CHAT}`, cwd: '../backend', url: `http://127.0.0.1:${CHAT}/health`, reuseExistingServer: false, timeout: 30_000 },
    // E2E_PYTHON (absolute, also used by mcp.spec.ts) overrides the backend venv's Python
    { command: `${process.env.E2E_PYTHON || '.venv/bin/python'} -m aiosmtpd -n -l 127.0.0.1:${SMTP} -c aiosmtpd.handlers.Sink`, cwd: '../backend', port: SMTP, reuseExistingServer: false, timeout: 30_000 },
    {
      command: `${process.env.E2E_UVICORN || '.venv/bin/uvicorn'} ${ENTRYPOINT} --host 127.0.0.1 --port ${API}`,
      cwd: '../backend', url: `http://127.0.0.1:${API}/api/health`, reuseExistingServer: false, timeout: 60_000,
      env: { STUDIO_DB: db, STUDIO_E2E_DRIVE_FIXTURE: DRIVE ? '1' : '0', STUDIO_E2E_EXPENSE_FIXTURE: EXPENSE ? '1' : '0', STUDIO_IMPORT_DIR: path.join(os.tmpdir(), 'lgs-e2e-imports'), OPENAI_API_KEY: '', STUDIO_ENABLE_DEMO_TOOLS: '1', STUDIO_ENABLE_CODE_NODES: '1', STUDIO_ENABLE_BROWSER: '1', STUDIO_CODE_RUNTIME: process.env.E2E_CODE_RUNTIME || 'docker',  // Code mode (TASK-0055/0056): E2E_CODE_RUNTIME=subprocess runs code-subprocess.spec.ts
         STUDIO_MCP_STDIO: '1', STUDIO_RUN_TIMEOUT: '5', STUDIO_ALLOW_PRIVATE_CALLBACKS: '1', STUDIO_SMTP_ALLOW_PRIVATE: '1', STUDIO_PUBLIC_URL: `http://127.0.0.1:${UI}`,  // links in e-mail / Teams approvals (TASK-0047)
        STUDIO_PUBLIC_CHAT_RATE_READ: '0',  // isolate UI cases sharing one IP; backend tests assert transport throttling
        ...(CHANNEL_SMTP ? { SMTP_HOST: '127.0.0.1', SMTP_PORT: String(SMTP), SMTP_FROM: 'fixture@example.test', SMTP_STARTTLS: '0', SMTP_USER: '', SMTP_PASSWORD: '', SMTP_SSL: '0' } : {}),
        STUDIO_MCP_ALLOW_PRIVATE: '1',  // managed actions use the local fake Telegram API; production keeps its default SSRF guard
        STUDIO_WEBHOOK_BACKOFF_BASE: '0.5', STUDIO_ATTACHMENT_STORAGE: process.env.E2E_ATTACHMENT_STORAGE || 'db', STUDIO_ATTACHMENT_FS_PATH: ATTACH_DIR,  // TASK-0195: E2E_ATTACHMENT_STORAGE=fs runs every spec on a folder
         SLACK_API_URL: `http://127.0.0.1:${CHAT}/slack`, TELEGRAM_API_URL: `http://127.0.0.1:${CHAT}/telegram`, WHATSAPP_API_URL: `http://127.0.0.1:${CHAT}/whatsapp` },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${UI} --strictPort`,
      url: `http://127.0.0.1:${UI}`, reuseExistingServer: false, timeout: 60_000,
      env: { STUDIO_API_PORT: String(API), STUDIO_UI_PORT: String(UI) },
    },
  ],
})
