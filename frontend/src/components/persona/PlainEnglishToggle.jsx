'use client'

import { usePersona } from '@/hooks/usePersona'

/**
 * PlainEnglishToggle — header toggle that switches between Simple and Technical mode.
 * Reads isSimple from PersonaContext and updates it on click.
 */
export default function PlainEnglishToggle() {
  const { isSimple, toggleSimple, persona } = usePersona()

  // Researcher always sees technical mode; don't show toggle
  if (persona === 'researcher') return null
  // No persona set yet — hide
  if (!persona) return null

  return (
    <button
      id="plain-english-toggle"
      onClick={toggleSimple}
      title={isSimple ? 'Switch to Technical mode' : 'Switch to Simple mode'}
      className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-white/10 hover:text-white"
    >
      <span className={isSimple ? 'text-astro-secondary' : 'text-slate-500'}>Simple</span>
      <span className="text-slate-600">/</span>
      <span className={!isSimple ? 'text-astro-secondary' : 'text-slate-500'}>Technical</span>
    </button>
  )
}
