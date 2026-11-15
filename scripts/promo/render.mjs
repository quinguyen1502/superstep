// Renders the intro video frame by frame and muxes the music bed.
// The frames come from the quickstart spec: HANDBOOK_SHOTS=1 npm run e2e -- quickstart (in frontend/).
//
//   node render.mjs --lang en                 -> handbook/docs/en/assets/video/studio-intro-en.mp4 (+ .jpg poster)
//   node render.mjs --lang vi --fps 30
//   node render.mjs --lang en --stills 15,31  -> build/stills/*.jpg, no video
//   node render.mjs --audio path/to/track.m4a -> a supplied track instead of music.mjs
//
// Uses the Playwright that frontend/ already installs (run `npm install` there first).
import { spawn, execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { chromePath, promoDir, repoRoot, buildDir, videoDir, framesDir } from './paths.mjs'

const { chromium } = await import(path.join(repoRoot, 'node_modules/playwright/index.mjs'))

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => {
  if (a.startsWith('--')) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true])
  return acc
}, []))
const lang = args.lang === 'vi' ? 'vi' : 'en'
const fps = Number(args.fps || 30)

const browser = await chromium.launch({ executablePath: chromePath(), args: ['--allow-file-access-from-files', '--force-color-profile=srgb', '--hide-scrollbars'] })
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
const flowFile = path.join(framesDir(lang), 'flow.json')
if (!fs.existsSync(flowFile)) throw new Error(`${flowFile} is missing: run HANDBOOK_SHOTS=1 npm run e2e -- quickstart in frontend/`)
await page.addInitScript(flow => { window.FLOW = flow }, JSON.parse(fs.readFileSync(flowFile, 'utf8')))
await page.addInitScript(strings => { window.STRINGS = strings }, JSON.parse(fs.readFileSync(path.join(promoDir, 'locales', `${lang}.json`), 'utf8')))
await page.goto(`file://${path.join(promoDir, 'video.html')}?lang=${lang}`, { waitUntil: 'load', timeout: 120000 })
await page.evaluate(async () => {
  await document.fonts.ready
  await Promise.all([...document.images].map(i => i.complete ? null : new Promise(r => { i.onload = i.onerror = r })))
})
const broken = await page.evaluate(() => [...document.images].filter(i => !i.naturalWidth).map(i => i.src))
if (broken.length) throw new Error('missing images:\n' + broken.join('\n'))

const at = t => page.evaluate(t => window.renderAt(t), t)
fs.mkdirSync(buildDir, { recursive: true })

if (args.stills) {
  const dir = path.join(buildDir, 'stills')
  fs.mkdirSync(dir, { recursive: true })
  for (const t of String(args.stills).split(',').map(Number)) {
    await at(t)
    const out = path.join(dir, `${lang}-${t.toFixed(1).padStart(5, '0')}.jpg`)
    await page.screenshot({ path: out, type: 'jpeg', quality: 85 })
    console.log('wrote', path.relative(repoRoot, out))
  }
  await browser.close()
  process.exit(0)
}

fs.mkdirSync(videoDir(lang), { recursive: true })
const out = path.resolve(args.out || path.join(videoDir(lang), `studio-intro-${lang}.mp4`))
const silent = path.join(buildDir, `silent-${lang}.mp4`)

await at(await page.evaluate(() => window.POSTER_AT))
await page.screenshot({ path: out.replace(/\.mp4$/, '.jpg'), type: 'jpeg', quality: 80 })

const duration = await page.evaluate(() => window.DURATION)
const speed = await page.evaluate(() => window.SPEED)
const frames = Math.round(duration * fps)
const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '24', '-pix_fmt', 'yuv420p', silent], { stdio: ['pipe', 'inherit', 'inherit'] })
const started = Date.now()
for (let i = 0; i < frames; i++) {
  await at(i / fps)
  const buf = await page.screenshot({ type: 'jpeg', quality: 94 })
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r))
  if (i % 300 === 0) console.log(`${lang} frame ${i}/${frames} ${((Date.now() - started) / 1000).toFixed(0)}s`)
}
ff.stdin.end()
const code = await new Promise(r => ff.on('close', r))
await browser.close()
if (code !== 0) throw new Error(`ffmpeg exited ${code}`)

const audio = args.audio ? path.resolve(args.audio) : path.join(buildDir, `music-${speed}x.wav`)
if (!args.audio && !fs.existsSync(audio)) execFileSync('node', [path.join(promoDir, 'music.mjs'), audio, String(speed)], { stdio: 'inherit' })
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', silent, '-i', audio,
  '-af', `afade=t=out:st=${duration - 3}:d=3`, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
  '-t', String(duration), '-movflags', '+faststart', out], { stdio: 'inherit' })
console.log('wrote', path.relative(repoRoot, out))
process.exit(0)
