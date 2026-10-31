import type { ReactNode } from 'react'

export default function PageHeader({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="font-semibold text-[28px] leading-tight">{title}</h1>
        <div className="mt-1 h-1 w-12 rounded-full bg-mint" aria-hidden />
        {description && <p className="mt-2 text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  )
}
