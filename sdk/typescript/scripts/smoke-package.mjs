// Exercise compiled conditional exports, not Vitest's source aliases.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)
for (const load of [name => import(name), name => require(name)]) {
  const root = await load('@superstep/sdk'), chat = await load('@superstep/sdk/chat'), server = await load('@superstep/sdk/server')
  assert.equal(root.VERSION, '0.2.0')
  assert.equal(typeof root.Superstep, 'function')
  assert.equal(typeof chat.ChatClient, 'function')
  assert.equal(typeof chat.createChatStore, 'function')
  assert.equal(root.mintChatToken, undefined)
  assert.equal(chat.mintChatToken, undefined)
  assert.equal(typeof server.mintChatToken, 'function')
}
console.log('ESM/CommonJS root, chat and server exports passed')
