import { APIConnectionError, errorFor } from './errors.js'

type Payload = { success?: boolean; data?: unknown; error?: { code?: string; message?: string; details?: unknown } } | null

/** Read the shared API error envelope. */
export async function envelope<T>(response: Response): Promise<T> {
  return unwrap<T>(response, await response.json().catch(() => null) as Payload)
}

export function unwrap<T>(response: Response, payload: Payload): T {
  if (!payload || typeof payload.success !== 'boolean' || (payload.success && (!response.ok || !('data' in payload)))) {
    throw new APIConnectionError(`Unexpected response (HTTP ${response.status}); is baseUrl a Superstep server?`, { code: 'BAD_RESPONSE', status: response.status })
  }
  if (!payload.success) {
    const error = payload.error ?? {}
    throw errorFor(response.status, error.code ?? 'UNKNOWN', error.message ?? `HTTP ${response.status}`, error.details, response.headers)
  }
  return payload.data as T
}

export function abortReason(signal?: AbortSignal): unknown {
  if (signal?.reason !== undefined) return signal.reason
  const error = new Error('The request was aborted'); error.name = 'AbortError'; return error
}

export function checkAbort(signal?: AbortSignal): void { if (signal?.aborted) throw abortReason(signal) }

/** Stop waiting for a host callback without requiring that callback to support AbortSignal. */
export function abortable<T>(promise: Promise<T>, signal?: AbortSignal): Promise<T> {
  checkAbort(signal)
  if (!signal) return promise
  return new Promise((resolve, reject) => {
    const abort = () => { signal.removeEventListener('abort', abort); reject(abortReason(signal)) }
    signal.addEventListener('abort', abort, { once: true })
    promise.then(resolve, reject).finally(() => signal.removeEventListener('abort', abort))
  })
}
