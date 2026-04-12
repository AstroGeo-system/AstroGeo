'use client'

import { useState } from 'react'
import { api } from '@/lib/api'

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

const AGENTS = [
  {
    icon: '🌍',
    name: 'Geospatial Agent',
    description: 'NDVI analysis, land cover change, vegetation loss detection',
    color: 'hover:bg-indigo-900/20 hover:border-indigo-500/30',
    testQuery: 'Which regions in India show the most vegetation loss?',
  },
  {
    icon: '☄️',
    name: 'Astronomy Agent',
    description: 'Asteroid risk scoring, anomaly detection, close approach tracking',
    color: 'hover:bg-orange-900/20 hover:border-orange-500/30',
    testQuery: 'What are the highest risk asteroids right now?',
  },
  {
    icon: '🌾',
    name: 'Agro-Climate Agent',
    description: 'Drought composite index, crop yield prediction, market prices',
    color: 'hover:bg-emerald-900/20 hover:border-emerald-500/30',
    testQuery: 'Which Maharashtra districts are most drought stressed?',
  },
  {
    icon: '⚡',
    name: 'Solar Flare Agent',
    description: 'Geomagnetic storm tracking, GPS disruption risk, irrigation impact',
    color: 'hover:bg-yellow-900/20 hover:border-yellow-500/30',
    testQuery: 'Did solar flares disrupt smart irrigation in Maharashtra?',
  },
]

const DATA_SOURCES = [
  'Sentinel-2 (ESA)',
  'NASA JPL Horizons',
  'NASA POWER API',
  'ISRO Bhoonidhi',
  'Neo4j GraphRAG',
  'NASA DONKI (Solar)',     // ← added
  'ERA5 Reanalysis (ECMWF)', // ← added
]

export default function AgentsDashboard() {
  const [activeQuery, setActiveQuery] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeAgent, setActiveAgent] = useState(null)

  const runAgentQuery = async (agent) => {
    setActiveAgent(agent.name)
    setLoading(true)
    setResult(null)
    try {
      const data = await api.query(agent.testQuery)
      setResult(data)
      setActiveQuery(agent.testQuery)
    } catch (e) {
      setResult({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0e121e] text-slate-200 font-body relative">
      {/* Top Navigation Bar */}
      <div className="flex items-center justify-between px-8 py-4 border-b border-white/5">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex flex-col items-center justify-center p-1 relative overflow-hidden shadow-[0_0_15px_rgba(99,102,241,0.5)]">
            <span className="text-xl z-10 relative drop-shadow">🚀</span>
            <div className="absolute inset-x-0 bottom-0 h-1/2 bg-white/20 blur-md pointer-events-none" />
          </div>
          <div>
            <h1 className="font-display font-bold text-xl text-white tracking-wide">AstroGeo</h1>
            <p className="text-xs text-slate-400">Autonomous Scientific Research Platform</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700/50 text-sm hover:bg-slate-700/50 transition font-medium">
            <span className="text-base">📊</span> Archive
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700/50 text-sm hover:bg-slate-700/50 transition font-medium">
            <span className="text-base">⚙️</span> Settings
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700/50 text-sm hover:bg-slate-700/50 transition font-medium">
            <span className="text-base">📚</span> Docs
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* LEFT — Agent list */}
          <div className="bg-[#111827]/80 border border-white/5 rounded-2xl p-8 backdrop-blur-sm">
            <h2 className="text-xs font-semibold tracking-[0.2em] text-slate-400 mb-6 uppercase">
              Active Agents
            </h2>

            <div className="space-y-4">
              {AGENTS.map(agent => (
                <button
                  key={agent.name}
                  onClick={() => runAgentQuery(agent)}
                  disabled={loading}
                  className={cn(
                    'w-full text-left flex items-start gap-4 p-5 rounded-xl border border-white/5 bg-slate-900/30 transition cursor-pointer group',
                    agent.color,
                    activeAgent === agent.name && 'border-indigo-500/40 bg-indigo-900/20',
                    loading && activeAgent === agent.name && 'animate-pulse'
                  )}
                >
                  <span className="text-2xl group-hover:scale-110 transition-transform mt-0.5">
                    {agent.icon}
                  </span>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-slate-200 font-semibold tracking-wide text-[15px]">
                      {agent.name}
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                      {agent.description}
                    </p>
                    <div className="flex items-center gap-1.5 mt-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                      <span className="text-xs text-slate-400">
                        {loading && activeAgent === agent.name ? 'Running...' : 'Online — click to query'}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            <h2 className="text-xs font-semibold tracking-[0.2em] text-slate-400 mt-10 mb-6 uppercase">
              Data Sources
            </h2>
            <div className="space-y-3">
              {DATA_SOURCES.map(source => (
                <div key={source} className="flex items-center gap-3 text-sm text-slate-300">
                  <svg className="w-4 h-4 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  {source}
                </div>
              ))}
            </div>
          </div>

          {/* RIGHT — Live result panel */}
          <div className="bg-[#111827]/80 border border-white/5 rounded-2xl p-8 backdrop-blur-sm flex flex-col">
            <h2 className="text-xs font-semibold tracking-[0.2em] text-slate-400 mb-6 uppercase">
              Agent Output
            </h2>

            {!result && !loading && (
              <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
                <span className="text-5xl opacity-30">🤖</span>
                <p className="text-slate-500 text-sm">
                  Click any agent to run a live query through the LangGraph pipeline
                </p>
              </div>
            )}

            {loading && (
              <div className="flex-1 flex flex-col items-center justify-center gap-4">
                <div className="animate-spin text-4xl">⟳</div>
                <p className="text-slate-400 text-sm">
                  Running through: Router → {activeAgent} → GraphRAG → Synthesiser
                </p>
              </div>
            )}

            {result && !loading && (
              <div className="flex-1 flex flex-col gap-4">
                {/* Query */}
                <div className="text-xs text-slate-500 italic border-l-2 border-indigo-500/40 pl-3">
                  "{activeQuery}"
                </div>

                {/* Domain + timing */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border border-indigo-500/40 bg-indigo-500/10 text-indigo-300">
                    {result.domain}
                  </span>
                  <span className="text-xs text-slate-500">
                    {result.processing_time_ms}ms
                  </span>
                  <span className="text-xs text-slate-500">
                    · {result.evidence_chain?.length} nodes traversed
                  </span>
                </div>

                {/* Answer */}
                <div className="text-slate-200 text-sm leading-relaxed bg-slate-900/40 rounded-xl p-4 border border-white/5 flex-1 overflow-y-auto">
                  {result.error ? (
                    <span className="text-rose-400">{result.error}</span>
                  ) : (
                    result.answer
                  )}
                </div>

                {/* Evidence chain */}
                {result.evidence_chain?.length > 0 && (
                  <div>
                    <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">
                      Evidence chain
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {result.evidence_chain.map((step, i) => (
                        <div key={i} className="flex items-center gap-1">
                          <span className="px-2 py-1 rounded bg-slate-800 border border-white/5 text-xs text-slate-300">
                            {step.step}
                          </span>
                          {i < result.evidence_chain.length - 1 && (
                            <span className="text-slate-600 text-xs">→</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}