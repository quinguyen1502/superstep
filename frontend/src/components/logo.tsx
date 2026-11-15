import { cn } from '@/lib/utils'

// Superstep "Step-up" mark. Theme tokens only: tile = primary, arrow = primary-foreground,
// exponent square = brand-accent. `mono` draws everything in currentColor (no tile fill).
export function LogoMark({ className, mono = false }: { className?: string; mono?: boolean }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={cn('size-7 shrink-0', className)} data-testid="logo-mark">
      {mono
        ? <rect x="1" y="1" width="30" height="30" rx="7" fill="none" stroke="currentColor" strokeWidth="2" />
        : <rect width="32" height="32" rx="8" className="fill-primary" />}
      <path d="M7 25 17 15M10 14h8v8" fill="none" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round"
        className={mono ? 'stroke-current' : 'stroke-primary-foreground'} />
      <rect x="20" y="4" width="8" height="8" rx="2.5" className={mono ? 'fill-current' : 'fill-brand-accent'} />
    </svg>
  )
}

/** Mark + product name. `showName` false renders the mark only (name kept for screen readers). */
export function Logo({ className, markClassName, showName = true, mono = false }:
  { className?: string; markClassName?: string; showName?: boolean; mono?: boolean }) {
  return (
    <span className={cn('flex items-center gap-2 font-semibold', className)}>
      <LogoMark className={markClassName} mono={mono} />
      {showName ? <span className="tracking-tight">Superstep</span> : <span className="sr-only">Superstep</span>}
    </span>
  )
}
