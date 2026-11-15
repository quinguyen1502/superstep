import { createContext, useContext } from 'react'
import type { Studio } from './use-studio'

/** The editor controller from `useStudio`, shared by the header and the four panels. */
export const StudioContext = createContext<Studio | null>(null)
export function useStudioCtx(): Studio {
  const s = useContext(StudioContext)
  if (!s) throw new Error('useStudioCtx must be used inside StudioContext')
  return s
}
