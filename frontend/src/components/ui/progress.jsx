import { cn } from '@/lib/cn'

export function Progress({ value = 0, className, indicatorClassName }) {
  const v = Math.min(100, Math.max(0, value))
  return (
    <div
      className={cn('relative h-2 w-full overflow-hidden rounded-full bg-white/10', className)}
    >
      <div
        className={cn(
          'h-full rounded-full bg-gradient-to-r from-astro-primary to-cyan-400 transition-all duration-500',
          indicatorClassName
        )}
        style={{ width: `${v}%` }}
      />
    </div>
  )
}
