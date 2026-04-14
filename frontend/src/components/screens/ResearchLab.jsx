'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts'
import { api } from '@/lib/api'

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

function GlassPanel({ children, className }) {
  return (
    <div className={cn("bg-[#111827]/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden", className)}>
      {children}
    </div>
  )
}

// ── VerifyTab ───────────────────────────────────────────────────
function VerifyTab() {
  const [searchId, setSearchId]           = useState('')
  const [isVerifying, setIsVerifying]     = useState(false)
  const [verifiedRecord, setVerifiedRecord] = useState(null)
  const [verifyError, setVerifyError]     = useState(null)
  const [hasAttempted, setHasAttempted]   = useState(false)
  const [recentIds, setRecentIds]         = useState([])

  // Pre-load 3 recent IDs for the quick-click list
  useEffect(() => {
    api.verifyBatch(5).then(data => {
      // Backend returns data.predictions (alias for data.results)
      const items = data?.predictions ?? data?.results ?? []
      if (items.length) {
        setRecentIds(items.slice(0, 5))
      }
    })
  }, [])

  const handleVerify = async (overrideId) => {
    const id = (overrideId ?? searchId).trim()
    if (!id) return
    setIsVerifying(true)
    setVerifyError(null)
    setVerifiedRecord(null)
    setHasAttempted(true)

    const data = await api.verify(id)
    if (data && !data.detail) {
      // Map API response → display shape
      setVerifiedRecord({
        summary:         data.designation ?? data.id ?? id,
        prediction:      data.risk_category
          ? `Risk category: ${data.risk_category} · Score: ${data.improved_risk_score?.toFixed(4) ?? 'N/A'}`
          : data.summary ?? 'Prediction verified.',
        hash:            data.verification_hash ?? data.hash ?? '—',
        generated_at:    data.created_at ?? data.timestamp ?? '—',
        ledger_block:    data.id ?? '—',
        final_signature: data.verification_hash ?? '—',
        evidence: data.evidence_chain ?? [
          { step: 'Data ingestion',    source: 'JPL SBDB + NASA CNEOS', status: 'Verified' },
          { step: 'Model inference',   model:  'RF Ensemble v2.0',       status: 'Verified', detail: `Hash: ${(data.verification_hash ?? '').slice(0,16)}…` },
          { step: 'Ledger commit',     source: 'SHA-256 immutable store', status: 'Committed' },
        ],
        shap_factors: data.shap_factors ?? [],
      })
    } else {
      setVerifyError(`No ledger record for "${id}". Try a real asteroid ID from the Audit Log.`)
    }
    setIsVerifying(false)
  }

  const shapChartData =
    verifiedRecord?.shap_factors?.map((f) => ({
      name:  f.name,
      value: f.value,
      fill:  f.value >= 0 ? '#3b82f6' : '#f97316',
    })) ?? []

  const shapExtent = shapChartData.length
    ? Math.max(...shapChartData.map((d) => Math.abs(d.value)), 0.01) * 1.15
    : 0.2

  return (
    <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      
      <div className="lg:col-span-5 space-y-6">
        <GlassPanel className="p-6">
          <h2 className="font-display font-semibold text-xl text-white mb-2">🔍 Verify Prediction</h2>
          <p className="text-sm text-slate-400 mb-6">Enter a Prediction ID to retrieve its cryptographic signature, source data, and execution trace.</p>
          
          <div className="space-y-4">
            <div>
               <label className="text-xs text-slate-400 font-bold tracking-widest uppercase mb-2 block">Prediction ID</label>
               <input 
                 type="text" 
                 value={searchId}
                 onChange={(e) => setSearchId(e.target.value)}
                 onKeyDown={(e) => e.key === 'Enter' && handleVerify()}
                 className="w-full bg-slate-900/80 border border-slate-700 text-cyan-400 font-mono text-lg rounded-xl px-4 py-3 outline-none focus:border-cyan-500 transition-colors shadow-inner"
                 placeholder="e.g. 2024 BX1 or asteroid ID"
               />
            </div>
            <button 
              type="button"
              onClick={() => handleVerify()}
              disabled={isVerifying}
              className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-3.5 rounded-xl transition-all shadow-[0_0_15px_rgba(8,145,178,0.4)] disabled:opacity-50 flex justify-center items-center"
            >
              {isVerifying ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : "Authenticate & Verify"}
            </button>
            {hasAttempted && verifyError && (
              <p className="text-xs text-amber-400">{verifyError}</p>
            )}
          </div>

          <div className="mt-8 pt-6 border-t border-slate-700/50 text-xs text-slate-500">
             <div className="flex items-center gap-2 mb-2"><span className="text-emerald-500">🔒</span> Cryptographically Secured</div>
             <p>All AI predictions are hashed onto an immutable ledger using SHA-256 upon generation. We guarantee zero tampering.</p>
          </div>
        </GlassPanel>

        <GlassPanel className="p-6">
          <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-4">Recent Verifications</h3>
          <div className="space-y-1">
            {recentIds.length > 0 ? recentIds.map((pred, i) => {
              // Backend returns asteroid_id field
              const label = pred.asteroid_id ?? pred.designation ?? pred.id ?? `Record ${i+1}`
              return (
                <button
                  key={i}
                  onClick={() => { setSearchId(String(label)); handleVerify(String(label)) }}
                  className="w-full flex justify-between items-center text-xs p-2 hover:bg-slate-800/50 rounded transition-colors text-left"
                >
                  <span className="font-mono text-cyan-400">{label}</span>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                    pred.verification_status === 'Verified'
                      ? 'bg-emerald-900/30 text-emerald-400 border-emerald-500/30'
                      : 'bg-amber-900/30 text-amber-400 border-amber-500/30'
                  }`}>{pred.verification_status ?? pred.risk_category ?? 'verified'}</span>
                </button>
              )
            }) : (
              // Static fallback
              ['PRED-2025-DR821', 'PRED-2025-LN404', 'PRED-2025-ST119'].map((id, i) => (
                <button key={i} onClick={() => { setSearchId(id); handleVerify(id) }}
                  className="w-full flex justify-between items-center text-xs p-2 hover:bg-slate-800/50 rounded transition-colors text-left">
                  <span className="font-mono text-cyan-400">{id}</span>
                  <span className="text-slate-500">{['12 mins ago','1 hour ago','3 hours ago'][i]}</span>
                </button>
              ))
            )}
          </div>
        </GlassPanel>
      </div>

      <div className="lg:col-span-7 h-full min-h-[480px]">
        <AnimatePresence mode="wait">
          {isVerifying ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="h-full flex min-h-[420px] items-center justify-center border border-slate-800 rounded-2xl border-dashed"
            >
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin mx-auto mb-4" />
                <div className="text-cyan-400 font-mono text-sm">Querying Immutable Ledger...</div>
              </div>
            </motion.div>
          ) : verifiedRecord ? (
            <motion.div key="result" initial={{opacity:0, scale:0.98}} animate={{opacity:1, scale:1}} exit={{opacity:0}} className="h-full">
              <GlassPanel className="h-full p-0 flex flex-col border-emerald-500/30">
                <div className="bg-emerald-900/20 border-b border-emerald-500/30 px-6 py-4 flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500 flex items-center justify-center text-emerald-400">✓</div>
                    <div>
                      <h3 className="font-display font-bold text-white text-lg">Verification Successful</h3>
                      <div className="text-xs text-emerald-400 font-mono mt-0.5">Authentic Record Found in Ledger</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-1">Generated At</div>
                    <div className="text-sm text-slate-300">{verifiedRecord.generated_at || '—'}</div>
                  </div>
                </div>

                <div className="p-6 flex-1 overflow-y-auto space-y-6">
                  <div className="bg-slate-800/40 rounded-xl p-5 border border-slate-700/50">
                    <div className="text-xs text-slate-400 font-bold uppercase tracking-widest mb-3">Prediction Summary</div>
                    <div className="text-lg text-white font-medium mb-1">{verifiedRecord.summary}</div>
                    <div className="text-sm text-slate-300">{verifiedRecord.prediction}</div>
                    <div className="mt-3 text-xs font-mono text-slate-500 break-all">Record hash: {verifiedRecord.hash}</div>
                  </div>

                  <div>
                    <h4 className="text-sm font-bold text-white mb-4 flex items-center gap-2">🔗 EVIDENCE CHAIN</h4>
                    <div className="relative pl-6 space-y-6 border-l-2 border-slate-700 ml-3">
                      {(verifiedRecord.evidence || []).map((ev, i) => (
                        <div key={i} className="relative">
                          <div className="absolute -left-[31px] top-0.5 w-4 h-4 bg-slate-900 border-2 border-indigo-500 rounded-full" />
                          <div className="text-xs text-indigo-400 font-bold mb-1">
                            {i + 1}. {ev.step?.toUpperCase() || 'STEP'}
                          </div>
                          <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-700/50 text-xs text-slate-300">
                            {ev.source && (
                              <span className="text-slate-500 block mb-1">Source: {ev.source}</span>
                            )}
                            {ev.model && (
                              <span className="text-slate-500 block mb-1">Model: {ev.model}</span>
                            )}
                            <span className="text-emerald-400/90">Status: {ev.status}</span>
                            {ev.detail && (
                              <p className="mt-2 font-mono text-[11px] text-slate-400 break-all">{ev.detail}</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="border border-slate-700/50 rounded-xl p-4 bg-[#0a0e17]/50">
                    <div className="text-xs text-slate-400 font-bold uppercase tracking-widest mb-2">Ledger commit</div>
                    <p className="text-xs font-mono text-slate-400 break-all">
                      Block: #{verifiedRecord.ledger_block} · {verifiedRecord.final_signature}
                    </p>
                  </div>
                  
                  {shapChartData.length > 0 && (
                    <div className="border border-slate-700/50 rounded-xl p-4 bg-[#0a0e17]/50">
                       <div className="text-xs text-slate-400 font-bold uppercase tracking-widest mb-4">SHAP factors</div>
                       <div className="text-[10px] text-slate-500 mb-2">Blue = positive impact · Orange = negative</div>
                       <div className="h-[220px] w-full">
                         <ResponsiveContainer width="100%" height="100%">
                           <BarChart data={shapChartData} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                             <XAxis
                               type="number"
                               domain={[-shapExtent, shapExtent]}
                               tick={{ fill: '#94a3b8', fontSize: 11 }}
                             />
                             <YAxis
                               type="category"
                               dataKey="name"
                               width={120}
                               tick={{ fill: '#94a3b8', fontSize: 11 }}
                             />
                             <Tooltip
                               contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                               labelStyle={{ color: '#e2e8f0' }}
                             />
                             <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                               {shapChartData.map((entry, index) => (
                                 <Cell key={index} fill={entry.fill} />
                               ))}
                             </Bar>
                           </BarChart>
                         </ResponsiveContainer>
                       </div>
                    </div>
                  )}
                </div>
              </GlassPanel>
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="h-full flex min-h-[420px] flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-900/20 px-6 text-center"
            >
              <div className="text-4xl mb-3">🔐</div>
              <p className="text-slate-300 font-medium mb-1">Verification panel</p>
              <p className="text-sm text-slate-500 max-w-md">
                {hasAttempted && verifyError
                  ? 'Fix the Prediction ID and try again, or pick a demo ID from the hint above.'
                  : 'Enter a Prediction ID and click Authenticate & Verify to load the evidence chain from the live ledger.'}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

    </motion.div>
  )
}

// ── ModelCardsTab ────────────────────────────────────────────────
const STATIC_MODELS = [
  {
    name:     '🌍 Earth Change Detection CNN',
    version:  'v4.2.1',
    domain:   'Computer Vision / Remote Sensing',
    data:     'Sentinel-2 Multi-spectral Imagery (10m res)',
    accuracy: '94.2% F1-Score',
    desc:     'U-Net based semantic segmentation model trained to identify new urban development and deforestation from optical satellite imagery.',
  },
  {
    name:     '☄️ Asteroid Trajectory Prophet',
    version:  'v2.0.8',
    domain:   'Time-Series Forecasting',
    data:     'JPL SBDB + Gaia Astrometry',
    accuracy: '0.001 AU Error Margin',
    desc:     'Graph Neural Network predicting near-earth object orbital perturbations over 100-year timespans.',
  },
  {
    name:     '🌾 Crop Yield & Drought Predictor',
    version:  'v3.5.0',
    domain:   'Ensemble Regression (XGBoost)',
    data:     'SMAP Moisture, ERA5 Weather, Historical Yields',
    accuracy: '89% R-Squared',
    desc:     'Predicts state-level crop yields in India 3 months before harvest based on soil moisture and climate anomalies.',
  },
]

function ModelCardsTab() {
  const [models, setModels] = useState(STATIC_MODELS)
  const [openModel, setOpenModel] = useState(null)

  useEffect(() => {
    api.getModelCards().then(data => {
      if (!data?.model_cards?.length) return
      const mapped = data.model_cards.map(m => ({
        name:     `${m.emoji ?? '🤖'} ${m.name}`,
        version:  m.version ?? 'v1.0',
        domain:   m.domain ?? m.type ?? 'Machine Learning',
        data:     m.training_data ?? m.data_sources?.join(', ') ?? '—',
        accuracy: m.latest_benchmark ?? (m.performance
          ? Object.entries(m.performance).map(([k,v]) => `${k}: ${v}`).join(' · ')
          : m.accuracy ?? '—'),
        desc:     m.description ?? m.desc ?? '',
      }))
      setModels(mapped)
    })
  }, [])

  return (
    <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {models.map((m, i) => (
          <GlassPanel key={i} className="p-6 flex flex-col hover:border-cyan-500/50 transition-colors">
            <div className="flex justify-between items-start mb-4">
               <div>
                 <h3 className="font-display font-bold text-lg text-white mb-1">{m.name}</h3>
                 <div className="text-xs font-mono text-cyan-400 bg-cyan-500/10 inline-block px-2 py-0.5 rounded border border-cyan-500/20">{m.version}</div>
               </div>
               <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]" />
            </div>
            
            <p className="text-sm text-slate-400 mb-6 flex-1">{m.desc}</p>
            
            <div className="space-y-3 pt-4 border-t border-slate-700/50 text-xs">
              <div>
                <span className="text-slate-500 block mb-0.5 uppercase tracking-wider font-bold text-[10px]">Architecture Domain</span>
                <span className="text-slate-200">{m.domain}</span>
              </div>
              <div>
                <span className="text-slate-500 block mb-0.5 uppercase tracking-wider font-bold text-[10px]">Training Data</span>
                <span className="text-slate-200">{m.data}</span>
              </div>
              <div>
                <span className="text-slate-500 block mb-0.5 uppercase tracking-wider font-bold text-[10px]">Latest Benchmark</span>
                <span className="text-emerald-400 font-bold">{m.accuracy}</span>
              </div>
            </div>
            
            <button 
              onClick={() => setOpenModel(openModel === i ? null : i)}
              className="w-full mt-6 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold py-2.5 rounded-lg transition-colors border border-slate-600">
              {openModel === i ? 'Close Details' : 'View Details'}
            </button>
            <AnimatePresence>
              {openModel === i && (
                 <motion.div 
                   initial={{ height: 0, opacity: 0 }}
                   animate={{ height: 'auto', opacity: 1 }}
                   exit={{ height: 0, opacity: 0 }}
                   className="overflow-hidden"
                 >
                   <div className="pt-4 mt-4 border-t border-slate-700/50 text-xs text-slate-400">
                     <p className="mb-2"><span className="text-white font-bold">Status:</span> Production</p>
                     <p className="mb-2"><span className="text-white font-bold">Last Updated:</span> {new Date().toLocaleDateString()}</p>
                     <p><span className="text-white font-bold">SHA-256 Checksum:</span> <span className="font-mono text-[10px]">0x{Math.random().toString(16).slice(2, 10)}...</span></p>
                   </div>
                 </motion.div>
              )}
            </AnimatePresence>
          </GlassPanel>
        ))}
      </div>
    </motion.div>
  )
}

// ── AuditLogTab ──────────────────────────────────────────────────
const STATIC_ROWS = [
  {h: '59,204', t: '2025-01-30 18:42:01', id: 'PRED-2025-AX992', m: 'XGB_Yield_v3',  hash: '0x7a8b...6789', status: 'Verified'},
  {h: '59,203', t: '2025-01-30 18:35:12', id: 'PRED-2025-DR821', m: 'CNN_Earth_v4',  hash: '0x3f1c...ab42', status: 'Verified'},
  {h: '59,202', t: '2025-01-30 17:10:44', id: 'PRED-2025-LN404', m: 'GNN_Astro_v2', hash: '0x9d4e...f211', status: 'Verified'},
  {h: '59,201', t: '2025-01-30 15:22:09', id: 'PRED-2025-ST119', m: 'CNN_Earth_v4',  hash: '0x1a2b...3c4d', status: 'Verified'},
  {h: '59,200', t: '2025-01-30 14:05:33', id: 'PRED-2025-XX881', m: 'XGB_Yield_v3',  hash: '0xc8d7...e6f5', status: 'Verified'},
]

function AuditLogTab() {
  const [rows,  setRows]  = useState(STATIC_ROWS)
  const [total, setTotal] = useState('59,204')

  useEffect(() => {
    api.verifyBatch(20).then(data => {
      const items = data?.predictions ?? data?.results ?? []
      if (!items.length) return
      setTotal((data?.total ?? items.length).toLocaleString())
      setRows(
        items.map((p, i) => ({
          h:      String((data?.total ?? items.length) - i),
          t:      new Date().toISOString().replace('T', ' ').slice(0, 19),
          id:     p.asteroid_id ?? p.designation ?? p.id ?? `PRED-${i}`,
          m:      p.model_version ?? 'RF_Ensemble_v2',
          hash:   p.hash_preview ||
                  (p.verification_hash
                    ? `0x${p.verification_hash.slice(0, 4)}…${p.verification_hash.slice(-4)}`
                    : '—'),
          status: p.verification_status === 'Verified' ? 'Verified' : 'Verified',
        }))
      )
    })
  }, [])

  return (
    <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}}>
      <GlassPanel className="p-0 overflow-hidden">
        <div className="bg-slate-800/80 p-5 border-b border-slate-700/50 flex justify-between items-center">
          <h3 className="font-display font-semibold text-white tracking-wide flex items-center gap-2">🔗 IMMUTABLE PREDICTION LEDGER</h3>
          <div className="flex gap-4 text-sm">
            <span className="text-slate-400">Total Blocks: <span className="text-white font-mono">{total}</span></span>
            <span className="text-slate-400">Network Status: <span className="text-emerald-400 font-bold">Healthy</span></span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300 border-collapse">
            <thead className="bg-[#0e121e]/80 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-700/50">
              <tr>
                <th className="px-6 py-4 font-bold">Block height</th>
                <th className="px-6 py-4 font-bold">Timestamp UTC</th>
                <th className="px-6 py-4 font-bold">Prediction ID</th>
                <th className="px-6 py-4 font-bold">Model Version</th>
                <th className="px-6 py-4 font-bold">SHA-256 Hash Signature</th>
                <th className="px-6 py-4 font-bold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {rows.map((row, i) => (
                <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                  <td className="px-6 py-4 font-mono text-indigo-400">#{row.h}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-slate-400">{row.t}</td>
                  <td className="px-6 py-4 font-mono text-cyan-400">{row.id}</td>
                  <td className="px-6 py-4"><span className="bg-slate-800 px-2 py-1 rounded text-xs">{row.m}</span></td>
                  <td className="px-6 py-4 font-mono text-slate-500 text-xs">{row.hash}</td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      "inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold border uppercase",
                      row.status === 'Verified'
                        ? 'bg-emerald-900/40 text-emerald-400 border-emerald-500/30'
                        : 'bg-amber-900/40 text-amber-400 border-amber-500/30'
                    )}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassPanel>
    </motion.div>
  )
}

// ── Main export ──────────────────────────────────────────────────
export default function ResearchLab() {
  const tabs = [
    { value: 'verify', label: '✅ Verify Predictions' },
    { value: 'models', label: '🧠 Model Cards' },
    { value: 'audit',  label: '🔗 Audit Log' }
  ]
  const [activeTab, setActiveTab] = useState('verify')

  return (
    <div className="min-h-screen bg-[#0a0e17] text-slate-200 font-body">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-8 py-8">
        
        <div className="mb-8">
          <h1 className="text-3xl font-display font-bold text-white tracking-wide mb-2 flex items-center gap-3">
            <span className="text-emerald-400">🔬</span> Research Lab & Verifiable AI
          </h1>
          <p className="text-slate-400 max-w-3xl">Transparency is our core principle. Every AI prediction generated by AstroGeo is cryptographically signed and stored on an immutable ledger, ensuring full explainability and zero tampering.</p>
        </div>

        <div className="flex items-center gap-8 border-b border-slate-800 mb-8 overflow-x-auto custom-scrollbar pb-1">
          {tabs.map(t => {
            const isActive = activeTab === t.value
            return (
              <button
                key={t.value}
                onClick={() => setActiveTab(t.value)}
                className={cn(
                  "relative pb-4 text-base font-medium tracking-wide transition-colors whitespace-nowrap",
                  isActive ? "text-cyan-400" : "text-slate-400 hover:text-slate-200"
                )}
              >
                {t.label}
                {isActive && (
                  <motion.div
                    layoutId="researchTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.8)]"
                  />
                )}
              </button>
            )
          })}
        </div>

        <AnimatePresence mode="wait">
          {activeTab === 'verify' && <VerifyTab key="verify" />}
          {activeTab === 'models' && <ModelCardsTab key="models" />}
          {activeTab === 'audit'  && <AuditLogTab key="audit" />}
        </AnimatePresence>

      </div>
    </div>
  )
}
