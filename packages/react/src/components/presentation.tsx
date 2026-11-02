import { createContext, useContext, type ReactNode } from 'react'

/** Host-owned capabilities. Studio navigation and child-run reads never enter the shared package. */
export type ChatPresentation = { portalContainer?: HTMLElement | null; childStep?: (runId: string, name?: string) => ReactNode; reviewerLink?: (label: string) => ReactNode }
const Presentation = createContext<ChatPresentation>({})
export const ChatPresentationProvider = Presentation.Provider
export const useChatPresentation = () => useContext(Presentation)
