import { useSyncExternalStore } from 'react'

const subscribe = (cb: () => void) => { addEventListener('resize', cb); return () => removeEventListener('resize', cb) }
/** The window's inner width, updated on resize. */
export const useViewportWidth = () => useSyncExternalStore(subscribe, () => window.innerWidth, () => 1440)

/** Phone layout below Tailwind's `md` (768px), the same query as the `max-md:` classes. A media query, not innerWidth:
 *  on a phone a page wider than the screen widens innerWidth too. */
export const MOBILE_QUERY = '(max-width: 767.98px)'
const mq = () => window.matchMedia(MOBILE_QUERY)
const subscribeMobile = (cb: () => void) => { const m = mq(); m.addEventListener('change', cb); return () => m.removeEventListener('change', cb) }
export const useIsMobile = () => useSyncExternalStore(subscribeMobile, () => mq().matches, () => false)
