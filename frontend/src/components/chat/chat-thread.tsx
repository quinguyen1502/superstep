/** Studio capabilities remain here; the shared package owns the presentation. */
import type { ComponentProps } from 'react'
import { Link } from 'react-router-dom'
import { ChatThread as Thread, ChatPresentationProvider, type ChatPresentation } from '@superstep/react'
import { ChildSteps } from '@/components/run-trace'
export type { FileLinks } from '@superstep/react'

const presentation: ChatPresentation = {
  childStep: (runId, name) => <ChildSteps runId={runId} name={name} className="ml-0" />,
  reviewerLink: label => <Link to="/approvals">{label}</Link>,
}
export function ChatThread(props: ComponentProps<typeof Thread>) {
  return <ChatPresentationProvider value={presentation}><Thread {...props} /></ChatPresentationProvider>
}
