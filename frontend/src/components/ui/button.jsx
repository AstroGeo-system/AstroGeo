import { cn } from '@/lib/cn'

const variants = {
  default:
    'bg-astro-primary text-white hover:bg-astro-primary/90 shadow-[0_0_20px_rgba(11,61,145,0.35)]',
  secondary:
    'bg-astro-secondary text-[#0A0A0A] hover:bg-astro-secondary/90 shadow-[0_0_16px_rgba(255,107,53,0.25)]',
  outline:
    'border border-white/15 bg-transparent hover:bg-white/5 text-slate-100',
  ghost: 'hover:bg-white/5 text-slate-200',
}

export function Button({ className, variant = 'default', size = 'default', ...props }) {
  const sizes = {
    default: 'h-10 px-4 py-2 text-sm',
    sm: 'h-9 rounded-lg px-3 text-xs',
    lg: 'h-11 rounded-lg px-8',
    icon: 'h-9 w-9',
  }
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-astro-primary/50 disabled:pointer-events-none disabled:opacity-50',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  )
}
