'use client'

import { motion } from 'framer-motion'

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

export default function TabsUnderline({ tabs, active, onChange }) {
  return (
    <div className="glass px-3 py-2 rounded-2xl">
      <div className="relative flex items-center gap-8">
        {tabs.map((t) => {
          const isActive = t.value === active
          return (
            <button
              key={t.value}
              type="button"
              onClick={() => onChange?.(t.value)}
              className={cn(
                'relative py-2 text-sm transition-colors',
                isActive ? 'text-cyan-200' : 'text-slate-400 hover:text-slate-200'
              )}
            >
              {t.label}
              {isActive && (
                <motion.span
                  layoutId="tab-underline"
                  className="absolute -bottom-1 left-0 right-0 h-[2px] rounded-full bg-cyan-300/90 shadow-[0_0_18px_rgba(34,211,238,0.55)]"
                />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

