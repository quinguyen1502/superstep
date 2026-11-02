// Test-only launcher: ephemeral secrets are read from a private file, never argv or browser assets.
import { readFile } from 'node:fs/promises'
if (process.env.CHAT_HOST_DEMO !== '1' || !process.env.CHAT_HOST_FIXTURE) throw new Error('Explicit chat-host fixture configuration required')
const config = JSON.parse(await readFile(process.env.CHAT_HOST_FIXTURE, 'utf8'))
Object.assign(process.env, { CHAT_STUDIO_URL: config.baseUrl, CHAT_SLUG: config.human.slug,
  CHAT_KEY_ID: config.human.keyId, CHAT_KEY_SECRET: config.human.secret })
await import('../server.mjs')
