'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
import { api } from '@/lib/api'

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

const EXAMPLE_QUERIES = [
  { icon: '🌿', label: 'Vegetation Trends', query: 'Which regions in India show the most vegetation loss?' },
  { icon: '☄️', label: 'Asteroid Tracking', query: 'What are the highest risk asteroids right now?' },
  { icon: '🌧️', label: 'Drought Analysis', query: 'Which Maharashtra districts are most drought stressed?' },
  { icon: '🏙️', label: 'Urban Expansion', query: 'Which Indian zones show the most urban growth?' },
  { icon: '⚡', label: 'Solar Impact', query: 'Did solar flares disrupt smart irrigation in Maharashtra?' },
]

export default function ResearchQuery() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleAnalyze = async (overrideQuery) => {
    const q = overrideQuery || query
    if (!q.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await api.query(q)
      if (!data) throw new Error('No response from API')
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handlePillClick = (q) => {
    setQuery(q)
    handleAnalyze(q)
  }

  return (
    <div className="min-h-screen bg-[#0e121e] text-slate-200 font-body relative pb-16">
      {/* Top Navigation Bar */}
      <div className="flex items-center justify-between px-8 py-4 border-b border-white/5">
        <Link href="/" className="flex items-center gap-4 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex flex-col items-center justify-center p-1 relative overflow-hidden shadow-[0_0_15px_rgba(99,102,241,0.5)]">
            <span className="text-xl z-10 relative drop-shadow group-hover:scale-110 transition-transform">🚀</span>
            <div className="absolute inset-x-0 bottom-0 h-1/2 bg-white/20 blur-md pointer-events-none" />
          </div>
          <div>
            <h1 className="font-display font-bold text-xl text-white tracking-wide">AstroGeo</h1>
            <p className="text-xs text-slate-400">Autonomous Scientific Research Platform</p>
          </div>
        </Link>
        <div className="flex items-center gap-4">
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700/50 text-sm hover:bg-slate-700/50 transition font-medium">
            <span className="text-base text-cyan-400">📊</span> Archive
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700/50 text-sm hover:bg-slate-700/50 transition font-medium">
            <span className="text-base text-slate-300">⚙️</span> Settings
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700/50 text-sm hover:bg-slate-700/50 transition font-medium">
            <span className="text-base text-rose-400">📚</span> Docs
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">

        {/* Main Research Container */}
        <div className="bg-[#111827]/80 border border-white/5 rounded-2xl p-8 backdrop-blur-sm">
          <h2 className="text-2xl font-semibold text-white tracking-wide mb-6">
            What would you like to research?
          </h2>

          <div className="relative mb-6">
            <textarea
              className="w-full bg-[#1e2436]/50 border border-slate-700/50 rounded-2xl px-5 py-4 text-sm text-slate-200 placeholder:text-slate-500 placeholder:font-light outline-none focus:border-indigo-500/50 focus:bg-[#1e2436] transition-colors resize-none h-[110px]"
              placeholder="Ask anything... e.g., 'Show me vegetation change in Thane over the last 5 years' or 'When is the next asteroid flyby visible from Pune?'"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleAnalyze()
                }
              }}
            />
            <div className="absolute bottom-4 right-4">
              {/* CHANGED: was <Link href="/timeline">, now a button */}
              <button
                onClick={() => handleAnalyze()}
                disabled={loading || !query.trim()}
                className="inline-flex items-center gap-2 px-6 py-2 rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-sm transition-colors shadow-[0_0_15px_rgba(99,102,241,0.4)]"
              >
                {loading ? (
                  <>
                    <span className="animate-spin">⟳</span> Analyzing...
                  </>
                ) : (
                  <>Analyze →</>
                )}
              </button>
            </div>
          </div>

          {/* Pills — now clickable with real queries */}
          <div className="flex flex-wrap items-center gap-3">
            {EXAMPLE_QUERIES.map(pill => (
              <button
                key={pill.label}
                onClick={() => handlePillClick(pill.query)}
                className="flex items-center gap-2 px-4 py-1.5 rounded-full border border-slate-700/50 bg-slate-800/30 text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
              >
                <span className="text-base">{pill.icon}</span> {pill.label}
              </button>
            ))}
          </div>
        </div>

        {/* Result Panel — NEW, only shows after query */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-rose-900/20 border border-rose-500/30 rounded-2xl p-6 text-rose-300 text-sm"
            >
              ⚠️ {error}
            </motion.div>
          )}

          {result && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="bg-[#111827]/80 border border-indigo-500/20 rounded-2xl p-8 backdrop-blur-sm space-y-6"
            >
              {/* Domain badge + timing */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border border-indigo-500/40 bg-indigo-500/10 text-indigo-300">
                    {result.domain}
                  </span>
                  <span className="text-xs text-slate-500">
                    {result.processing_time_ms}ms · {result.evidence_chain?.length} evidence steps
                  </span>
                </div>
                <span className="text-xs text-emerald-400 font-medium">✓ Verified</span>
              </div>

              {/* Answer */}
              <div className="text-slate-200 text-sm leading-relaxed bg-slate-900/40 rounded-xl p-5 border border-white/5">
                {result.answer}
              </div>

              {/* Evidence chain */}
              <div>
                <h4 className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-3">
                  Evidence Chain
                </h4>
                <div className="flex flex-wrap items-center gap-2">
                  {result.evidence_chain?.map((step, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className="px-3 py-1.5 rounded-lg bg-slate-800/60 border border-white/5 text-xs text-slate-300">
                        <span className="text-indigo-400 font-medium">{step.step}</span>
                        {step.source && (
                          <span className="text-slate-500 ml-1">· {step.source}</span>
                        )}
                      </div>
                      {i < result.evidence_chain.length - 1 && (
                        <span className="text-slate-600">→</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Stats Cards — UNCHANGED */}
        <div className="grid grid-cols-1 mb-6">
          <div className="bg-[#111827]/80 border border-white/5 rounded-2xl p-8 flex flex-col justify-between relative overflow-hidden group hover:border-white/10 transition-colors">
            <div className="absolute right-8 top-8 text-2xl opacity-60 group-hover:opacity-100 transition-opacity drop-shadow">📦</div>
            <h3 className="text-xs font-semibold tracking-[0.2em] text-slate-400 uppercase mb-4">Archive Depth</h3>
            <div className="text-5xl font-bold text-indigo-400 mb-2 drop-shadow-md">8.2 TB</div>
            <div className="text-sm text-slate-400">Historical satellite & orbital data stored</div>
          </div>
        </div>

        <div className="grid grid-cols-1">
          <div className="bg-[#111827]/80 border border-white/5 rounded-2xl p-8 flex flex-col justify-between relative overflow-hidden group hover:border-white/10 transition-colors">
            <div className="absolute right-8 top-8 text-2xl opacity-60 group-hover:opacity-100 transition-opacity drop-shadow">⏳</div>
            <h3 className="text-xs font-semibold tracking-[0.2em] text-slate-400 uppercase mb-4">Temporal Range</h3>
            <div className="text-5xl font-bold text-indigo-400 mb-2 drop-shadow-md">10 Years</div>
            <div className="text-sm text-slate-400">Continuous observation timeline</div>
          </div>
        </div>

      </div>
    </div>
  )
}