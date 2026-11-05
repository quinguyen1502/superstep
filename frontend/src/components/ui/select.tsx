import type { ComponentProps } from 'react'
import { useTranslation } from 'react-i18next'
import { SelectContent as SharedSelectContent } from '@superstep/react/ui/select'
export * from '@superstep/react/ui/select'

/** Empty lookups still open a visible, accessible menu. :has also handles empty SelectGroups/fragments. */
export function SelectContent({ children, position = 'popper', emptyMessage, ...props }: ComponentProps<typeof SharedSelectContent> & { emptyMessage?: string }) {
  const { t } = useTranslation()
  return <SharedSelectContent position={position} {...props}>
    <div className="[&:has([data-slot=select-item])>[data-slot=select-empty]]:hidden">
      {children}
      <p data-slot="select-empty" role="status" className="px-3 py-3 text-sm text-muted-foreground">{emptyMessage || t('common.noOptions')}</p>
    </div>
  </SharedSelectContent>
}
