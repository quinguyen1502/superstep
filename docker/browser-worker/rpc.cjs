// Docker-exec stdin is the trusted control channel. Never print input or raw worker errors.
const http = require('node:http')
const chunks = []; let size = 0
process.stdin.on('data', chunk => { size += chunk.length; if (size > 256 * 1024) process.exit(2); chunks.push(chunk) })
process.stdin.on('end', () => {
  let value
  try { value = JSON.parse(Buffer.concat(chunks).toString('utf8')) } catch { process.exit(2) }
  if (!['open', 'command', 'approve', 'artifact', 'close', 'health', 'inspect', 'renew', 'supervisor_health'].includes(value.method)) process.exit(2)
  const body = JSON.stringify(value.body)
  const request = http.request({ socketPath: '/tmp/browser-control.sock', path: `/v1/${value.method}`, method: 'POST',
    headers: { 'content-type': 'application/json', 'content-length': Buffer.byteLength(body) }, timeout: 65000 }, response => {
    const output = []; let count = 0
    response.on('data', chunk => { count += chunk.length; if (count > 4 * 1024 * 1024) process.exit(2); output.push(chunk) })
    response.on('end', () => { if (response.statusCode !== 200) process.exit(2); process.stdout.write(Buffer.concat(output)) })
  })
  request.on('error', () => process.exit(2)); request.on('timeout', () => { request.destroy(); process.exit(2) }); request.end(body)
})
