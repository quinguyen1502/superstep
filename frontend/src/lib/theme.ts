import { useEffect, useState } from 'react'

const initial = () => new URLSearchParams(location.search).get('theme') || localStorage.getItem('theme') || 'light'
let current = initial() === 'dark'
const subs = new Set<(d: boolean) => void>()
document.documentElement.classList.toggle('dark', current)
export function useTheme() {
  const [dark, setD] = useState(current)
  useEffect(() => { subs.add(setD); return () => { subs.delete(setD) } }, [])
  const setDark = (d: boolean) => { current = d; localStorage.setItem('theme', d ? 'dark' : 'light'); document.documentElement.classList.toggle('dark', d); subs.forEach(f => f(d)) }
  return { dark, setDark }
}

/** Pages for people outside the studio (the public chat, TASK-0142) follow the browser's light or dark setting unless a
 *  theme was chosen here or passed as ?theme=. Nothing is stored. */
export function useSystemTheme() {
  useEffect(() => {
    if (new URLSearchParams(location.search).get('theme') || localStorage.getItem('theme')) return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const apply = () => { current = mq.matches; document.documentElement.classList.toggle('dark', current); subs.forEach(f => f(current)) }
    apply(); mq.addEventListener('change', apply); return () => mq.removeEventListener('change', apply)
  }, [])
}
