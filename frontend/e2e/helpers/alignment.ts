import { expect, type Locator } from '@playwright/test'

/** Alignment guardrails (docs/ui-conventions.md, rule 11). */
export type Box = { name: string; top: number; height: number; centre: number }

/** Wait until the element's open animations (a dialog's zoom and fade) have finished or been cancelled: boxes measured mid-zoom are scaled. */
export async function settled(l: Locator) {
  await l.evaluate(el => Promise.allSettled(el.getAnimations({ subtree: true }).map(a => a.finished)))
}

async function boxes(locators: Locator[]): Promise<Box[]> {
  const out: Box[] = []
  for (const l of locators) {
    const b = await l.boundingBox({ timeout: 5_000 })
    if (!b) throw new Error(`alignment: ${l} is not visible`)
    out.push({ name: l.toString().replace(/^locator\(|\)$/g, ''), top: +b.y.toFixed(2), height: +b.height.toFixed(2), centre: +(b.y + b.height / 2).toFixed(2) })
  }
  return out
}

/** Every locator shares the first one's vertical centre and (unless `sameHeight: false`) its height, within `tolerance` px.
 * Use `sameHeight: false` for rows that mix a control with a label, a Switch or a Badge. */
export async function expectRowAligned(locators: Locator[], { tolerance = 1, sameHeight = true, label = 'row' }: { tolerance?: number; sameHeight?: boolean; label?: string } = {}) {
  if (locators.length < 2) throw new Error(`alignment: ${label} needs at least two visible elements, got ${locators.length}`)
  const bs = await boxes(locators), [ref] = bs
  const bad = bs.filter(b => Math.abs(b.centre - ref.centre) > tolerance || (sameHeight && Math.abs(b.height - ref.height) > tolerance))
  expect.soft(bad, `${label} misaligned against ${ref.name} (top ${ref.top}, h ${ref.height}, centre ${ref.centre}):\n${bad.map(b => `  ${b.name}: top ${b.top}, h ${b.height}, centre ${b.centre}`).join('\n')}`).toEqual([])
  return bs
}

/** The text baseline of each locator's first text run: a zero-size inline-block probe sits on the baseline
 * (`vertical-align: baseline`), so its top is the baseline whatever the font's ascender/descender metrics.
 * Box centres are not enough: two fonts (or sizes) with the same box centre can still sit on different baselines. */
export async function baselines(locators: Locator[]): Promise<{ name: string; baseline: number }[]> {
  const out = []
  for (const l of locators) {
    const baseline = await l.evaluate(el => {
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, { acceptNode: n => n.textContent!.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP })
      const text = walker.nextNode() as Text | null
      if (!text) throw new Error('alignment: no text node')
      // wrap the text run and the probe in one inline box, so a flex parent (Button, Badge) cannot turn the probe into its own flex item
      const wrap = document.createElement('span'), probe = document.createElement('span')
      probe.style.cssText = 'display:inline-block;width:0;height:0;padding:0;margin:0;border:0;vertical-align:baseline'
      text.parentNode!.insertBefore(wrap, text); wrap.append(text, probe)
      const y = probe.getBoundingClientRect().top
      wrap.parentNode!.insertBefore(text, wrap); wrap.remove(); return y
    })
    out.push({ name: l.toString().replace(/^locator\(|\)$/g, ''), baseline: +baseline.toFixed(2) })
  }
  return out
}

/** Every locator's text sits on the first one's baseline, within `tolerance` px (default 0.5). */
export async function expectBaselineAligned(locators: Locator[], { tolerance = 0.5, label = 'text' }: { tolerance?: number; label?: string } = {}) {
  if (locators.length < 2) throw new Error(`alignment: ${label} needs at least two visible elements, got ${locators.length}`)
  const bs = await baselines(locators), [ref] = bs
  const bad = bs.filter(b => Math.abs(b.baseline - ref.baseline) > tolerance)
  expect.soft(bad, `${label} baselines differ from ${ref.name} (${ref.baseline}):\n${bad.map(b => `  ${b.name}: ${b.baseline}`).join('\n')}`).toEqual([])
  return bs
}
