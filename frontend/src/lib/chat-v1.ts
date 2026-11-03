/** Keep the Studio trace presentation while the public page speaks the versioned wire protocol. */
import type { RunEvent } from './trace'

export function v1ChatRequest(session: string, request: Record<string, unknown>, locale: string) {
  const base = { chat_session_id: session, locale }
  return 'response' in request
    ? { ...base, type: 'answer', response: request.response, ...(request.node ? { node: request.node } : {}) }
    : { ...base, type: 'message', text: request.message, ...(request.attachment_ids ? { attachments: request.attachment_ids } : {}),
      ...(request.edit_operation_id ? { edit_operation_id: request.edit_operation_id } : {}) }
}

export function v1ChatEvent(frame: RunEvent & { event?: string }): RunEvent | undefined {
  switch (frame.type) {
    case 'token': return { ...frame, type: 'node_token' }
    case 'step': {
      const type = { started: 'node_started', finished: 'node_finished', error: 'error' }[frame.event ?? '']
      return type ? { ...frame, type } : undefined
    }
    case 'question': return { ...frame, type: 'run_waiting' }
    case 'done': return { ...frame, type: 'run_summary' }
    case 'run_started': case 'error': return frame
    default: return undefined // additive frame types never become unknown Studio trace events
  }
}
