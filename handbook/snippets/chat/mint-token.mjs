import { createHmac } from 'node:crypto'

// Server only. Read keyId/secret from your secret manager, and userId/name
// from the authenticated user in your own application.
export function mintChatToken({ keyId, secret, slug, userId, name = '' }) {
  const now = Math.floor(Date.now() / 1000)
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString('base64url')
  const header = encode({ alg: 'HS256', typ: 'JWT', kid: keyId })
  const claims = encode({ iss: keyId, aud: `superstep-chat:${slug}`,
    sub: userId, name, iat: now, exp: now + 600 })
  const unsigned = `${header}.${claims}`
  const signature = createHmac('sha256', secret).update(unsigned).digest('base64url')
  return `${unsigned}.${signature}`
}
