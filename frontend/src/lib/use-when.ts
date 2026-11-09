/** Small state hooks shared by dialogs and settings panels. */
import { useEffect, useEffectEvent, useState } from 'react'

/** Run `fn` when `active` becomes true, and again when `key` changes while active. Dialogs and settings panels reset
 *  their fields and load their data this way; `fn` always sees the latest props and state. */
export function useLoadWhen(active: boolean, fn: () => void, key?: unknown) {
  const run = useEffectEvent(fn)
  useEffect(() => { if (active) run() }, [active, key])
}

/** Call `fn` during render when `value` changes (React's "adjust state when a prop changes" pattern), e.g. to reset a
 *  local copy of a prop. Runs before paint, with no extra effect pass. */
export function useOnChange<T>(value: T, fn: (value: T) => void) {
  const [prev, setPrev] = useState(value)
  if (!Object.is(prev, value)) { setPrev(value); fn(value) }
}
