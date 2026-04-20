'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { usePersona } from '@/hooks/usePersona'
import { api } from '@/lib/api'

// ── U1: Persona-aware suggestions ────────────────────────────────
const PERSONA_SUGGESTIONS = {
  farmer: [
    'Is it safe to irrigate in Marathwada this week?',
    'Did any solar storms affect my crops recently?',
    'What is the drought risk in Vidarbha right now?',
    'Which zones have the worst vegetation health in 2024?',
  ],
  student: [
    'How does a geomagnetic storm disrupt GPS signals?',
    'What makes an asteroid anomalous in AstroGeo?',
    'Explain the cross-domain solar-agriculture link',
    'How was the launch probability model trained?',
  ],
  journalist: [
    'What is the biggest space weather story right now?',
    'Did the May 2024 solar storm affect Indian farmers?',
    'Which Indian regions face the highest drought risk?',
    'What are the top risk asteroids approaching Earth?',
  ],
  researcher: [
    'Which asteroids have the highest kinetic_energy_proxy score?',
    'Show the 4-hop graph path for the Kp9.0 May 2024 event',
    'What are the top SHAP drivers for launch failure?',
    'Run cross-domain query: solar flares and ISRO launches',
  ],
  policymaker: [
    'How many Indian districts are at high drought risk?',
    'What is the economic impact of the May 2024 solar storm?',
    'How reliable is the ISRO launch probability model?',
    'Which zones showed the most vegetation loss in 2024?',
  ],
}

// ── U1: Persona-aware placeholder text ───────────────────────────
const PERSONA_PLACEHOLDER = {
  farmer:      'Ask about your crops, drought risk, or weather...',
  student:     'Ask anything about space weather, asteroids, or satellites...',
  journalist:  'Ask for the latest story on space weather or Indian agriculture...',
  researcher:  'Run a cross-domain query or inspect model outputs...',
  policymaker: 'Ask about regional risk, economic impact, or mission data...',
}

/**
 * AskAstroGeo — plain English GraphRAG search box.
 * U1: Persona-aware suggestions + placeholder.
 * U2: Sends simplify=true for non-researcher / simple-mode users.
 */
export default function AskAstroGeo({ prefill }) {
  const { persona, personaConfig, isSimple, isResearcher } = usePersona()

  const suggestions = PERSONA_SUGGESTIONS[persona] ??
    PERSONA_SUGGESTIONS[personaConfig?.id] ??
    PERSONA_SUGGESTIONS.researcher

  const placeholder = PERSONA_PLACEHOLDER[persona] ??
    PERSONA_PLACEHOLDER[personaConfig?.id] ??
    PERSONA_PLACEHOLDER.researcher

  const [query, setQuery]               = useState(prefill ?? '')
  const [loading, setLoading]           = useState(false)
  const [result, setResult]             = useState(null)
  const [error, setError]               = useState(null)
  const [evidenceOpen, setEvidenceOpen] = useState(false)

  // U2: determine simplify flag — send simplify=true unless researcher in technical mode
  const shouldSimplify = !isResearcher && isSimple

  const handleAsk = async (q) => {
    const finalQ = (q ?? query).trim()
    if (!finalQ) return
    setLoading(true)
    setResult(null)
    setError(null)
    setEvidenceOpen(false)
    try {
      const data = await api.query(finalQ, shouldSimplify)
      setResult(data)
    } catch {
      setError('Could not reach the AI. Please make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const showChips = query.trim() === '' && !result && !loading

  return (
    <div className="w-full">
      {/* Search row */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            id="ask-astrogeo-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            placeholder={placeholder}
            className="w-full rounded-xl border border-white/10 bg-white/[0.04] py-3 pl-11 pr-4 text-sm text-slate-200 placeholder:text-slate-500 outline-none focus:border-astro-primary/60 focus:bg-white/[0.06] transition-colors"
          />
        </div>
        <button
          id="ask-astrogeo-btn"
          onClick={() => handleAsk()}
          disabled={loading}
          className="flex h-12 items-center gap-2 rounded-xl bg-astro-primary px-5 text-sm font-semibold text-white shadow-[0_0_20px_rgba(11,61,145,0.4)] transition hover:bg-astro-primary/90 disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Ask'}
        </button>
      </div>

      {/* U1: Persona-aware suggestion chips (shown only when input is empty) */}
      <AnimatePresence>
        {showChips && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-2.5 flex flex-wrap gap-2"
          >
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => { setQuery(s); handleAsk(s) }}
                className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-slate-400 transition hover:border-white/20 hover:text-slate-200 hover:bg-white/[0.06]"
              >
                {s}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Result */}
      <AnimatePresence>
        {(result || error) && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.25 }}
            className="mt-4 rounded-xl border border-white/10 bg-white/[0.04] p-5"
          >
            {error && <p className="text-sm text-amber-400">{error}</p>}

            {result && (
              <>
                {/* Domain badge */}
                {result.domain && result.domain !== 'unknown' && (
                  <span className="mb-3 inline-block rounded-full border border-astro-secondary/40 bg-astro-secondary/10 px-3 py-1 text-xs font-semibold text-astro-secondary">
                    {result.domain}
                  </span>
                )}

                {/* Answer */}
                <p className="text-sm leading-relaxed text-slate-200">
                  {result.answer ?? result.response ?? 'No answer returned.'}
                </p>

                {/* Evidence chain (collapsed, shown if researcher or technical mode) */}
                {result.evidence_chain?.length > 0 && (isResearcher || !isSimple) && (
                  <div className="mt-4">
                    <button
                      onClick={() => setEvidenceOpen(v => !v)}
                      className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-300 transition"
                    >
                      {evidenceOpen
                        ? <ChevronDown className="h-3.5 w-3.5" />
                        : <ChevronRight className="h-3.5 w-3.5" />}
                      {evidenceOpen ? 'Hide' : 'Show'} evidence chain ({result.evidence_chain.length} nodes)
                    </button>

                    <AnimatePresence>
                      {evidenceOpen && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="mt-3 space-y-2 border-l-2 border-astro-primary/30 pl-4">
                            {result.evidence_chain.map((node, i) => (
                              <div key={i} className="text-xs text-slate-400">
                                <span className="text-astro-secondary font-medium">
                                  {i + 1}. {node.label ?? node.step ?? node.name ?? node.id ?? `Node ${i + 1}`}
                                </span>
                                {node.source && (
                                  <span className="ml-2 text-slate-500">· {node.source}</span>
                                )}
                                {node.domain && (
                                  <span className="ml-2 text-slate-500">· {node.domain}</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
