import { describe, expect, it } from 'vitest'
import { bucketTotal, fmtAge, fmtCount, fmtShare, fmtUsd } from '../usage'

describe('usage formatting', () => {
  it('formats counts, money and shares', () => {
    expect(fmtCount(12345, 'en')).toBe('12,345')
    expect(fmtUsd(0.01234, 'en')).toBe('$0.0123')
    expect(fmtUsd(12.345, 'en')).toBe('$12.35')
    expect(fmtUsd(0, 'en')).toBe('$0.00')
    expect(fmtShare(0.5, 'en')).toBe('50%')
    expect(fmtShare(0.1234, 'en')).toBe('12.3%')
  })
  it('shows a dash when a share is unknown (no runs)', () => {
    expect(fmtShare(null, 'en')).toBe('—')
    expect(fmtShare(undefined, 'en')).toBe('—')
  })
  it('picks the largest whole unit for ages', () => {
    expect(fmtAge(null)).toBeNull()
    expect(fmtAge(42.4)).toEqual({ n: 42, unit: 's' })
    expect(fmtAge(720)).toEqual({ n: 12, unit: 'min' })
    expect(fmtAge(3 * 3600 + 5)).toEqual({ n: 3, unit: 'h' })
    expect(fmtAge(2 * 86400 + 10)).toEqual({ n: 2, unit: 'd' })
  })
  it('sums a bucket across statuses', () => {
    expect(bucketTotal({ start: 0, ok: 3, error: 1, timeout: 1, cancelled: 0, other: 2 })).toBe(7)
    expect(bucketTotal({ start: 0, ok: 0, error: 0, timeout: 0, cancelled: 0, other: 0 })).toBe(0)
  })
})
