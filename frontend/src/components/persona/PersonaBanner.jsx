'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { usePersona } from '@/hooks/usePersona'

// ── U6: Static per-persona description lines ─────────────────────
const PERSONA_DESCRIPTIONS = {
  farmer:      'Showing agricultural risk, drought alerts, and weather data relevant to farming.',
  student:     'Full science content with explanations — technical scores available on request.',
  journalist:  'Story-first view: data narratives, impact figures, and regional risk summaries.',
  policymaker: 'Regional risk overview, economic impact data, and mission reliability statistics.',
}

/**
 * PersonaBanner — shows current persona + description + switch button.
 * Hidden for Researcher (per spec).
 * U6: Added one-line description below persona name.
 */
export default function PersonaBanner({ onSwitch }) {
  const { persona, personaConfig, visibility } = usePersona()

  if (!persona || !visibility.showPersonaBanner) return null

  const description = PERSONA_DESCRIPTIONS[persona]

  return (
    <AnimatePresence>
      <motion.div
        key="persona-banner"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.3 }}
        className={`
          flex items-start justify-between gap-4 rounded-xl border px-4 py-3 text-sm
          ${personaConfig?.borderClass ?? 'border-white/10'}
          ${personaConfig?.bgClass ?? 'bg-white/5'}
          mb-5
        `}
      >
        <div className="min-w-0 flex-1">
          {/* Row 1: emoji + label */}
          <div className="flex items-center gap-2 text-slate-300">
            <span className="text-base">{personaConfig?.emoji}</span>
            <span>
              Viewing as:{' '}
              <span className={`font-semibold ${personaConfig?.colorClass ?? 'text-white'}`}>
                {personaConfig?.label}
              </span>
            </span>
          </div>
          {/* U6: Row 2 — persona description */}
          {description && (
            <p className="mt-1 text-xs text-slate-500 leading-snug">
              {description}
            </p>
          )}
        </div>

        <button
          onClick={onSwitch}
          className="shrink-0 self-start rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-white/10 hover:text-white"
        >
          Switch Persona
        </button>
      </motion.div>
    </AnimatePresence>
  )
}
