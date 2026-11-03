export const fmtMs = (ms?: number) => ms == null ? '—' : ms < 1 ? `${ms.toFixed(2)} ms` : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`
