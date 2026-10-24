// Typed errors, mapped from the API's stable error codes (docs/api-errors.md), then from the HTTP status.

export interface ErrorInit {
  code?: string
  status?: number
  details?: unknown
  headers?: Headers
}

export class SuperstepError extends Error {
  readonly code: string
  readonly status?: number
  readonly details?: unknown
  readonly headers?: Headers

  constructor(message: string, init: ErrorInit = {}) {
    super(message)
    this.name = new.target.name
    this.code = init.code ?? 'UNKNOWN'
    this.status = init.status
    this.details = init.details
    this.headers = init.headers
  }
}

/** Missing base URL, token or workflow id. */
export class ConfigError extends SuperstepError {}
/** The request did not reach the server, or the response was not the API envelope. */
export class APIConnectionError extends SuperstepError {}
/** 401 TRIGGER_TOKEN_INVALID: missing, invalid or revoked token, or a token of another workflow. */
export class AuthenticationError extends SuperstepError {}
/** 404, e.g. RUN_NOT_FOUND. */
export class NotFoundError extends SuperstepError {}
/** 400 / 422: RUN_INPUT_INVALID, CALLBACK_URL_INVALID, VALIDATION_ERROR (see `details`). */
export class InvalidRequestError extends SuperstepError {}
/** 413 RUN_INPUT_TOO_LARGE. */
export class PayloadTooLargeError extends SuperstepError {}
/** 5xx, e.g. INTERNAL_ERROR. */
export class ServerError extends SuperstepError {}

/** 429 RATE_LIMITED. `retryAfter` is the number of seconds to wait. */
export class RateLimitError extends SuperstepError {
  get retryAfter(): number | undefined {
    const value = Number(this.headers?.get('retry-after'))
    return Number.isFinite(value) && this.headers?.has('retry-after') ? value : undefined
  }
}

/** `runAndWait` / `wait` gave up before the run finished. `run` is the last state seen. */
export class WaitTimeoutError<R = unknown> extends SuperstepError {
  readonly run: R
  constructor(message: string, run: R) {
    super(message, { code: 'WAIT_TIMEOUT' })
    this.run = run
  }
}

type ErrorClass = new (message: string, init?: ErrorInit) => SuperstepError

export const BY_CODE: Record<string, ErrorClass> = {
  TRIGGER_TOKEN_INVALID: AuthenticationError,
  RUN_NOT_FOUND: NotFoundError,
  WORKFLOW_NOT_FOUND: NotFoundError,
  NOT_FOUND: NotFoundError,
  RUN_INPUT_INVALID: InvalidRequestError,
  CALLBACK_URL_INVALID: InvalidRequestError,
  VALIDATION_ERROR: InvalidRequestError,
  BAD_REQUEST: InvalidRequestError,
  RUN_INPUT_TOO_LARGE: PayloadTooLargeError,
  PAYLOAD_TOO_LARGE: PayloadTooLargeError,
  RATE_LIMITED: RateLimitError,
  INTERNAL_ERROR: ServerError,
}
const BY_STATUS: Record<number, ErrorClass> = {
  400: InvalidRequestError, 401: AuthenticationError, 404: NotFoundError, 413: PayloadTooLargeError, 422: InvalidRequestError, 429: RateLimitError,
}

export function errorFor(status: number, code: string, message: string, details?: unknown, headers?: Headers): SuperstepError {
  const Cls = BY_CODE[code] ?? BY_STATUS[status] ?? (status >= 500 ? ServerError : SuperstepError)
  return new Cls(message, { code, status, details, headers })
}
