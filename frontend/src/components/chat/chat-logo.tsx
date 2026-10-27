/** A published chat's logo and its stand-ins (TASK-0145, REQ-0074): the uploaded image, or the first letter of the chat's
 *  title in a primary square; both are squares with rounded corners (the root's radius, `rounded-md` unless the caller
 *  sets one); and the illustration the page's welcome shows when the chat has no logo. Theme tokens only,
 *  so both follow light and dark. */
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { cn } from 'cn'
import { initialOf } from '@/lib/chat'

export function ChatLogo({ src, title, className, id, size }: { src?: string; title: string; className?: string; id?: string; size?: 'sm' | 'default' | 'lg' }) {
  return <Avatar className={cn('rounded-md after:rounded-[inherit]', className)} id={id} size={size} data-logo={src ? 'image' : 'initial'}>
    {src && <AvatarImage src={src} alt="" className="rounded-[inherit] bg-background object-contain" />}
    <AvatarFallback className="rounded-[inherit] bg-primary font-semibold text-primary-foreground" aria-hidden="true">{initialOf(title)}</AvatarFallback>
  </Avatar>
}

/** Two speech bubbles and a spark: the welcome picture of a chat without a logo. */
export function ChatIllustration({ className }: { className?: string }) {
  return <svg viewBox="0 0 160 120" className={cn('w-40 text-primary', className)} aria-hidden="true" id="public-chat-illustration">
    <circle cx="80" cy="60" r="56" className="fill-muted" />
    <path d="M30 30h66a10 10 0 0 1 10 10v26a10 10 0 0 1-10 10H54l-14 12V76H30a10 10 0 0 1-10-10V40a10 10 0 0 1 10-10Z"
      className="fill-background stroke-border" strokeWidth="2" />
    <rect x="34" y="44" width="48" height="6" rx="3" className="fill-muted-foreground/40" />
    <rect x="34" y="56" width="32" height="6" rx="3" className="fill-muted-foreground/25" />
    <path d="M78 58h50a10 10 0 0 1 10 10v20a10 10 0 0 1-10 10h-4v12l-14-12H78a10 10 0 0 1-10-10V68a10 10 0 0 1 10-10Z"
      fill="currentColor" />
    <circle cx="90" cy="78" r="4" className="fill-primary-foreground" />
    <circle cx="103" cy="78" r="4" className="fill-primary-foreground/80" />
    <circle cx="116" cy="78" r="4" className="fill-primary-foreground/60" />
    <path d="M128 20l3 8 8 3-8 3-3 8-3-8-8-3 8-3Z" fill="currentColor" />
  </svg>
}
