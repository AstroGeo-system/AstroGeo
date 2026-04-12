import { cn } from '@/lib/cn'

export function Input({ className, type = 'text', ...props }) {
  return (
    <input
      type={type}
      className={cn(
        'flex h-10 w-full rounded-lg border border-white/10 bg-[#0A0A0A]/80 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-astro-primary/40',
        className
      )}
      {...props}
    />
  )
}
