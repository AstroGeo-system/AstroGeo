'use client'

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

export function Field({ label, value, accent = false, className }) {
  return (
    <div className={cn('space-y-0.5', className)}>
      <div className="text-[11px] uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div
        className={cn(
          'text-sm text-slate-100',
          accent && 'text-cyan-200 font-medium'
        )}
      >
        {value}
      </div>
    </div>
  )
}

