// Host application API: its cookie stays on this origin; Superstep receives only a short-lived JWT.
export async function api<T>(path: string, json?: unknown): Promise<T> {
  const response = await fetch(path, { method: json === undefined ? 'GET' : 'POST', credentials: 'same-origin', headers: json === undefined ? {} : { 'Content-Type': 'application/json' }, body: json === undefined ? undefined : JSON.stringify(json) })
  const envelope = await response.json()
  if (!response.ok || !envelope.success) throw Object.assign(new Error(envelope.error?.message), envelope.error)
  return envelope.data as T
}
