import { useEffect, useEffectEvent, useState } from 'react'
import { api, ApiError, sessionExpired, signedIn, wsUrl } from '@/lib/api'
import { datasetUrl } from '@/lib/datasets'

type DatasetRevision = { schema_revision: number; data_revision: number }

const CHECK_INTERVAL = 5_000
const HEALTHY_CHECK_INTERVAL = 60_000
const HEARTBEAT_TIMEOUT = 45_000
const HANDSHAKE_TIMEOUT = 2_000
const COALESCE_DELAY = 150

export function isDatasetAccessError(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403 || error.code === 'DATASET_NOT_FOUND')
}

/** The socket only carries revision markers. The grid reads through the authorized snapshot APIs. */
export function useDatasetLive(id: string, onAccessLost: () => void) {
  const [revision, setRevision] = useState<DatasetRevision | null>(null)
  const [delayed, setDelayed] = useState(false)
  const loseAccess = useEffectEvent(onAccessLost)

  useEffect(() => {
    let stopped = false
    let connected = false
    let socket: WebSocket | undefined
    let next: DatasetRevision | undefined
    let socketEpoch = 0
    let lastCheck = Date.now()
    let reconnectDelay = 1_000
    let check: AbortController | undefined
    let flushTimer: number | undefined
    let reconnectTimer: number | undefined
    let healthTimer: number | undefined
    const endpoint = `${datasetUrl(id)}/revisions`

    const observe = (marker: DatasetRevision) => {
      next = marker
      if (flushTimer !== undefined) return
      flushTimer = window.setTimeout(() => {
        flushTimer = undefined
        const observed = next
        if (!observed) return
        setRevision(previous => previous?.data_revision === observed.data_revision
          && previous.schema_revision === observed.schema_revision ? previous : observed)
      }, COALESCE_DELAY)
    }

    const stop = () => {
      stopped = true
      clearTimeout(flushTimer)
      clearTimeout(reconnectTimer)
      clearTimeout(healthTimer)
      check?.abort()
      socket?.close()
    }

    const denied = (expired = false) => {
      stop()
      loseAccess()
      if (expired) sessionExpired()
    }

    const checkRevision = () => {
      if (stopped || document.hidden || check) return
      if (!signedIn()) { denied(true); return }
      const controller = new AbortController()
      check = controller
      lastCheck = Date.now()
      const epoch = socketEpoch
      void api<DatasetRevision>(endpoint, { signal: controller.signal }).then(marker => {
        // An older HTTP snapshot must not supersede a socket observation that arrived in flight.
        if (!stopped && epoch === socketEpoch) observe(marker)
      }).catch(error => {
        if (stopped) return
        if (isDatasetAccessError(error)) denied()
        else if (!connected) setDelayed(true)
      }).finally(() => { check = undefined })
    }

    const connect = () => {
      if (stopped) return
      if (!signedIn()) { denied(true); return }
      const stream = new WebSocket(wsUrl(`/ws/datasets/${encodeURIComponent(id)}/changes`))
      socket = stream
      healthTimer = window.setTimeout(() => stream.close(), HANDSHAKE_TIMEOUT)
      stream.onmessage = ({ data }) => {
        if (stopped || stream !== socket) return
        let event: Partial<DatasetRevision> & { type?: string }
        try { event = JSON.parse(data) } catch { return }
        if (!event) return
        if ((event.type === 'ready' || event.type === 'dataset_changed')
          && typeof event.data_revision === 'number' && typeof event.schema_revision === 'number') {
          socketEpoch++
          observe({ data_revision: event.data_revision, schema_revision: event.schema_revision })
          if (event.type === 'ready') {
            connected = true
            reconnectDelay = 1_000
            setDelayed(false)
          }
        }
        if (connected && ['ready', 'dataset_changed', 'ping'].includes(event.type ?? '')) {
          clearTimeout(healthTimer)
          healthTimer = window.setTimeout(() => stream.close(), HEARTBEAT_TIMEOUT)
        }
      }
      stream.onclose = ({ code }) => {
        if (stopped || stream !== socket) return
        clearTimeout(healthTimer)
        connected = false
        if (code === 4401 || code === 4403) { denied(code === 4401); return }
        setDelayed(true)
        checkRevision()
        reconnectTimer = window.setTimeout(connect, reconnectDelay)
        reconnectDelay = Math.min(reconnectDelay * 2, 30_000)
      }
    }

    const checkSession = (event: StorageEvent) => {
      if ((event.key === 'session_exp' || event.key === null) && !signedIn()) denied(true)
    }
    connect()
    const fallback = window.setInterval(() => {
      if (!connected || Date.now() - lastCheck >= HEALTHY_CHECK_INTERVAL) checkRevision()
    }, CHECK_INTERVAL)
    document.addEventListener('visibilitychange', checkRevision)
    window.addEventListener('focus', checkRevision)
    window.addEventListener('online', checkRevision)
    window.addEventListener('storage', checkSession)
    return () => {
      stop()
      clearInterval(fallback)
      document.removeEventListener('visibilitychange', checkRevision)
      window.removeEventListener('focus', checkRevision)
      window.removeEventListener('online', checkRevision)
      window.removeEventListener('storage', checkSession)
    }
  }, [id])

  return { revision, delayed }
}
