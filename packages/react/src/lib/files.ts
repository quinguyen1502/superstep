export async function downloadFile(url: string, name: string, headers?: Record<string, string>) {
  const r = await fetch(url, { headers: { 'X-Requested-With': 'studio', ...headers } })
  if (!r.ok) throw new Error(String(r.status))
  const href = URL.createObjectURL(await r.blob())
  const a = Object.assign(document.createElement('a'), { href, download: name }); document.body.append(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}

