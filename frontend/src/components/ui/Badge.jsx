'use client'

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

export default function Badge({ children, tone = 'cyan', className }) {
  const tones = {
    cyan: 'bg-cyan-400/10 text-cyan-200 border-cyan-300/25',
    green: 'bg-emerald-400/10 text-emerald-200 border-emerald-300/25',
    amber: 'bg-amber-400/10 text-amber-200 border-amber-300/25',
    red: 'bg-rose-400/10 text-rose-200 border-rose-300/25',
    purple: 'bg-fuchsia-400/10 text-fuchsia-200 border-fuchsia-300/25',
  }
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium',
        tones[tone] ?? tones.cyan,
        className
      )}
    >
      {children}
    </span>
  )
}

