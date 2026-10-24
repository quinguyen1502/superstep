// Fails when src/schema.ts is not what `npm run gen` would write from docs/api/openapi.public.json.
import { execSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
const file = new URL('../src/schema.ts', import.meta.url)
const before = readFileSync(file, 'utf8')
execSync('npm run --silent gen', { stdio: 'inherit' })
if (readFileSync(file, 'utf8') !== before) {
  console.error('src/schema.ts was out of date and has been regenerated: commit it (npm run gen).')
  process.exit(1)
}
