'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import dynamic from 'next/dynamic'
import { api } from '@/lib/api'

const IsroSatelliteMap = dynamic(() => import('./IsroSatelliteMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-slate-900 rounded-xl">
      <div className="w-10 h-10 border-4 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
    </div>
  )
})

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

// ── SatellitesTab ────────────────────────────────────────────────
function SatellitesTab() {
  const [fleet, setFleet] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getIsroFleet().then(data => {
      if (data) setFleet(data)
      setLoading(false)
    })
  }, [])

  return (
    <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-160px)] min-h-[600px]">
      
      {/* Fleet Map */}
      <div className="lg:col-span-7 h-full">
        <GlassPanel className="h-full w-full p-6 flex flex-col relative overflow-hidden">
          <div className="flex justify-between items-center mb-6 z-10">
            <h2 className="font-display font-semibold text-lg text-white flex items-center gap-2">
              🛰️ ISRO SATELLITE FLEET ({fleet.length} Active)
            </h2>
            <div className="flex gap-2">
              <select className="bg-slate-900/80 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1.5 outline-none">
                <option>All Types</option>
                <option>Remote Sensing</option>
                <option>Communication</option>
                <option>SAR / Navigation</option>
              </select>
            </div>
          </div>

          <div className="flex-1 w-full h-full relative">
            {loading ? (
               <div className="absolute inset-0 flex flex-col items-center justify-center">
                 <div className="w-10 h-10 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-4" />
                 <span className="text-slate-400 text-sm">Intercepting N2YO Telemetry...</span>
               </div>
            ) : (
               <IsroSatelliteMap fleetData={fleet} className="absolute inset-0 w-full h-full" />
            )}
          </div>
        </GlassPanel>
      </div>

      {/* Satellite List — Live Telemetry */}
      <div className="lg:col-span-5 h-full">
        <GlassPanel className="h-full p-0 flex flex-col">
          <div className="px-6 py-5 border-b border-slate-700/50 bg-[#1e2436]/50">
            <h3 className="font-display font-bold text-lg text-white flex items-center gap-2">
              📡 LIVE TELEMETRY STREAM
              {!loading && <span className="flex h-2 w-2 ml-2"><span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-emerald-400 opacity-75"></span><span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span></span>}
            </h3>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
            {loading ? (
               <div className="text-center py-10 text-slate-500">Establishing downlink...</div>
            ) : fleet.length === 0 ? (
               <div className="text-center py-10 text-slate-500">No telemetry available</div>
            ) : (
              <>
                {/* Featured card for first satellite */}
                <div className="bg-slate-800/40 rounded-xl border border-orange-500/30 overflow-hidden relative group">
                  <div className="absolute top-0 left-0 w-1 h-full bg-orange-500" />
                  <div className="p-4 border-b border-slate-700/30 flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]" />
                        <h4 className="font-bold text-white text-lg">{fleet[0].name}</h4>
                      </div>
                      <div className="text-xs text-slate-400 mt-1">{fleet[0].type}</div>
                    </div>
                    <div className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-1 rounded text-[10px] font-bold tracking-wider uppercase">
                      {fleet[0].eclipsed ? 'Eclipse Mode' : 'Sunlit ✅'}
                    </div>
                  </div>
                  
                  <div className="p-4 grid grid-cols-2 gap-3 text-xs border-b border-slate-700/30">
                    <div className="bg-slate-900/50 p-2 rounded">
                      <span className="text-slate-500 block mb-0.5">Altitude</span>
                      <span className="text-slate-200">{Math.round(fleet[0].altitude_km)} km</span>
                    </div>
                    <div className="bg-slate-900/50 p-2 rounded">
                      <span className="text-slate-500 block mb-0.5">Lat / Lon</span>
                      <span className="text-slate-200 font-medium font-mono">{fleet[0].latitude.toFixed(2)}°, {fleet[0].longitude.toFixed(2)}°</span>
                    </div>
                  </div>

                  <div className="p-4 bg-orange-500/5">
                    <div className="flex justify-between items-center mb-2">
                      <div className="text-xs font-bold text-orange-400 flex items-center gap-1.5">🤖 AI HEALTH PREDICTION</div>
                      <div className="text-xs font-bold text-emerald-400">{fleet[0].health}/100 Score</div>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-1.5 mb-3">
                      <div className="bg-emerald-500 h-1.5 rounded-full" style={{width: `${fleet[0].health}%`}} />
                    </div>
                    <div className="mt-4 flex gap-2">
                      <button className="flex-1 bg-orange-500 hover:bg-orange-600 text-white text-xs font-semibold py-2 rounded transition-colors">📍 Track Live</button>
                      <button className="flex-1 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold py-2 rounded transition-colors border border-slate-600">✅ Verify Health</button>
                    </div>
                  </div>
                </div>

                {/* Remaining satellites */}
                {fleet.slice(1).map(sat => (
                  <div key={sat.name} className="bg-slate-800/40 rounded-xl border border-slate-700/50 p-4 hover:bg-slate-800/60 transition-colors cursor-pointer block">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]" />
                        <span className="text-sm font-medium text-slate-300">{sat.name}</span>
                        <span className="text-[10px] text-slate-500 bg-slate-700/50 px-1.5 py-0.5 rounded">{sat.type}</span>
                      </div>
                      <span className="text-xs text-emerald-400 font-bold">{sat.health}%</span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-400 mt-3 font-mono">
                      <div>Alt: <span className="text-slate-200">{Math.round(sat.altitude_km)} km</span></div>
                      <div>Pos: <span className="text-slate-200">{sat.latitude.toFixed(2)}°, {sat.longitude.toFixed(2)}°</span></div>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        </GlassPanel>
      </div>

    </motion.div>
  )
}

// ── ChandrayaanTab ───────────────────────────────────────────────
// Chandrayaan-3 landed August 23, 2023
const CHANDRAYAAN3_LANDING = new Date('2023-08-23T00:00:00Z')

function ChandrayaanTab() {
  const daysOnMoon = Math.floor((Date.now() - CHANDRAYAAN3_LANDING) / (1000 * 60 * 60 * 24))
  return (
    <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-7 space-y-6">
        <GlassPanel className="p-6">
          <h3 className="font-display font-bold text-lg text-white mb-1">📈 Launch Success/Failure Timeline</h3>
          <p className="text-xs text-slate-400 mb-4">Based on the 108-mission launch history used for risk model training.</p>
          <div className="space-y-3">
            {timeline.map((t) => {
              const total = t.success + t.failed
              const successPct = Math.round((t.success / total) * 100)
              return (
                <div key={t.period}>
                  <div className="flex justify-between text-xs text-slate-400 mb-1">
                    <span>{t.period}</span>
                    <span>{t.success}/{total} successful ({successPct}%)</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-2 bg-emerald-500 inline-block" style={{ width: `${(t.success / total) * 100}%` }} />
                    <div className="h-2 bg-rose-500 inline-block" style={{ width: `${(t.failed / total) * 100}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
        </GlassPanel>

        <GlassPanel className="p-6">
          <h3 className="font-display font-bold text-lg text-white mb-4">🚀 Vehicle-wise Reliability</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {vehicles.map((v) => (
              <div key={v.name} className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4">
                <div className="text-sm text-white font-semibold">{v.name}</div>
                <div className="text-xs text-slate-400 mt-1">{v.missions} missions</div>
                <div className="mt-3 text-2xl font-bold text-cyan-400">{v.successRate}%</div>
              </div>
            ))}
          </div>
        </GlassPanel>
      </div>

          <div className="grid grid-cols-2 gap-4 mb-8 relative z-10">
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-700/50">
              <div className="text-xs text-slate-500 uppercase font-bold tracking-widest mb-1">Days on Moon</div>
              <div className="text-3xl font-display font-bold text-white">{daysOnMoon}</div>
            </div>
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-700/50">
              <div className="text-xs text-slate-500 uppercase font-bold tracking-widest mb-1">Last Data</div>
              <div className="text-xl font-display font-bold text-slate-300 mt-1">3 hours ago</div>
            </div>
          </div>
          <p className="text-xs text-amber-300 mt-4">Monsoon season shows lower launch success in the historical training set.</p>
        </GlassPanel>

        <GlassPanel className="p-6">
          <h3 className="font-display font-bold text-lg text-white mb-4">🧠 Top SHAP Drivers</h3>
          <div className="space-y-3">
            {shap.map((f) => (
              <div key={f.feature}>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>{f.feature}</span>
                  <span>{f.impact.toFixed(2)}</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800">
                  <div className="h-2 rounded-full bg-indigo-500" style={{ width: `${f.impact * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </GlassPanel>
      </div>
    </motion.div>
  )
}

      <div className="space-y-6">
        <GlassPanel className="p-6 border-l-4 border-l-cyan-500">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-display font-bold text-xl text-white flex items-center gap-2">🚀 VIKRAM LANDER</h3>
            <span className="text-xs font-bold text-indigo-400 bg-indigo-500/10 px-2 py-1 rounded border border-indigo-500/20">Active (Sleep-Wake)</span>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm mb-4">
            <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50"><span className="text-slate-500 block text-xs">Location</span><span className="text-white font-medium">69.37°S, 32.32°E</span></div>
            <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50"><span className="text-slate-500 block text-xs">Battery</span><span className="text-emerald-400 font-medium">78%</span></div>
            <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/50 col-span-2"><span className="text-slate-500 block text-xs">External Temp</span><span className="text-blue-400 font-medium">-180°C (Lunar Night)</span></div>
          </div>
        </GlassPanel>

  return (
    <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-6 space-y-4">
        {missions.map((m) => (
          <GlassPanel key={m.title} className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-display font-bold text-white">{m.title}</h3>
                <p className="text-xs text-slate-400">{m.year} • {m.status}</p>
              </div>
            </div>
            <p className="text-sm text-slate-300 mt-3">{m.highlight}</p>
          </GlassPanel>
        ))}
      </div>

      <div className="lg:col-span-6">
        <GlassPanel className="p-6 h-full">
          <h3 className="font-display font-bold text-lg text-white mb-4">🌙 Chandrayaan-3 Mission Facts</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
            <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
              <div className="text-xs text-slate-400">Landing date</div>
              <div className="text-white font-semibold mt-1">23 Aug 2023</div>
            </div>
            <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
              <div className="text-xs text-slate-400">Vikram coordinates</div>
              <div className="text-white font-semibold mt-1">~69.37°S, 32.32°E</div>
            </div>
            <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
              <div className="text-xs text-slate-400">Pragyan traverse</div>
              <div className="text-white font-semibold mt-1">~103 metres</div>
            </div>
            <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
              <div className="text-xs text-slate-400">Surface ops contact</div>
              <div className="text-white font-semibold mt-1">Last contact Sep 2023</div>
            </div>
          </div>
          <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4">
            <h4 className="text-sm font-semibold text-cyan-300 mb-2">Key findings</h4>
            <ul className="text-sm text-slate-300 space-y-2">
              <li>• Sulfur and multiple elements identified in-situ by LIBS.</li>
              <li>• Near-surface thermal profile measured in the polar region.</li>
              <li>• First successful soft landing near the Moon's south polar area by India.</li>
            </ul>
          </div>
        </GlassPanel>
      </div>
    </motion.div>
  )
}

// ── Option 4: NavIC Constellation Status ────────────────────────
function NavICTab() {
  const navicSats = [
    'IRNSS-1B', 'IRNSS-1C', 'IRNSS-1D', 'IRNSS-1E', 'IRNSS-1F', 'IRNSS-1G', 'NVS-01',
  ]
  return (
    <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-7">
        <GlassPanel className="p-6 h-full">
          <h3 className="font-display font-bold text-lg text-white mb-2">🧭 NavIC / Indian Constellation Status</h3>
          <p className="text-xs text-slate-400 mb-5">Regional navigation service focused on India and nearby region.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4">
              <div className="text-xs text-slate-400">Constellation size</div>
              <div className="text-2xl font-bold text-white mt-1">7 satellites</div>
            </div>
            <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4">
              <div className="text-xs text-slate-400">Service status</div>
              <div className="text-2xl font-bold text-emerald-400 mt-1">Operational</div>
            </div>
            <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4">
              <div className="text-xs text-slate-400">India coverage</div>
              <div className="text-white font-semibold mt-1">Primary</div>
            </div>
            <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4">
              <div className="text-xs text-slate-400">Use-case tie-in</div>
              <div className="text-white font-semibold mt-1">Precision agriculture + geospatial planning</div>
            </div>
          </div>
        </GlassPanel>
      </div>
      <div className="lg:col-span-5">
        <GlassPanel className="p-6 h-full">
          <h3 className="font-display font-bold text-lg text-white mb-4">Satellite List</h3>
          <div className="space-y-2 max-h-[480px] overflow-auto pr-1">
            {navicSats.map((sat) => (
              <div key={sat} className="flex items-center justify-between bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2">
                <span className="text-sm text-slate-200">{sat}</span>
                <span className="text-xs text-emerald-400 font-semibold">healthy</span>
              </div>
            ))}
          </div>
        </GlassPanel>
      </div>
    </motion.div>
  )
}

// ── LaunchesTab — live probability + schedule ────────────────────
function LaunchesTab() {
  const [prob,     setProb]     = useState(null)
  const [schedule, setSchedule] = useState(null)
  const [loading,  setLoading]  = useState(true)

  useEffect(() => {
    Promise.all([
      api.getLaunchProb(),
      api.getLaunchSchedule(),
    ]).then(([p, s]) => {
      setProb(p)
      setSchedule(s)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const pct         = prob?.probability_pct ?? 0
  const riskLevel   = prob?.risk_level      ?? 'Unavailable'
  const riskColor   = riskLevel === 'Favorable' ? 'text-emerald-400' : riskLevel === 'Marginal' ? 'text-amber-400' : 'text-red-400'
  const launches    = schedule?.scheduled_launches ?? []
  const countdown   = schedule?.countdown ?? { days: 23, hours: 0, minutes: 0 }

  // Gauge arc calculation (SVG)
  const gaugeAngle  = (pct / 100) * 180
  const r           = 70
  const cx          = 90
  const cy          = 90
  const startAngle  = -180
  const endAngle    = startAngle + gaugeAngle
  const toRad       = (deg) => (deg * Math.PI) / 180
  const x1 = cx + r * Math.cos(toRad(startAngle))
  const y1 = cy + r * Math.sin(toRad(startAngle))
  const x2 = cx + r * Math.cos(toRad(endAngle))
  const y2 = cy + r * Math.sin(toRad(endAngle))
  const large = gaugeAngle > 180 ? 1 : 0

  return (
    <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="grid grid-cols-1 lg:grid-cols-12 gap-6">

      {/* Launch Probability Gauge */}
      <div className="lg:col-span-5">
        <GlassPanel className="p-6 h-full flex flex-col">
          <h2 className="font-display font-semibold text-lg text-white mb-6 flex items-center gap-2">
            🚀 LAUNCH PROBABILITY
            <span className="ml-auto text-xs text-slate-500">Sriharikota, India</span>
          </h2>

          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="w-10 h-10 border-4 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
            </div>
          ) : (
            <>
              {/* SVG Gauge */}
              <div className="flex justify-center mb-6">
                <svg width="180" height="110" viewBox="0 0 180 110">
                  {/* Background arc */}
                  <path
                    d={`M ${cx + r * Math.cos(toRad(-180))} ${cy + r * Math.sin(toRad(-180))} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
                    fill="none" stroke="#1e293b" strokeWidth="14" strokeLinecap="round"
                  />
                  {/* Filled arc */}
                  {pct > 0 && (
                    <path
                      d={`M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`}
                      fill="none"
                      stroke={pct >= 70 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#ef4444'}
                      strokeWidth="14"
                      strokeLinecap="round"
                    />
                  )}
                  {/* Center text */}
                  <text x={cx} y={cy + 8} textAnchor="middle" fill="white" fontSize="24" fontWeight="bold">{pct}%</text>
                  <text x={cx} y={cy + 24} textAnchor="middle" fill="#94a3b8" fontSize="9">PROBABILITY</text>
                </svg>
              </div>

              <div className={`text-center text-2xl font-bold ${riskColor} mb-2`}>{riskLevel}</div>

              {/* Weather breakdown */}
              {prob?.based_on_weather && (
                <div className="mt-4 space-y-2 bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
                  <div className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-3">Weather Inputs</div>
                  {Object.entries(prob.based_on_weather).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs">
                      <span className="text-slate-400 capitalize">{k.replace(/_/g, ' ')}</span>
                      <span className="text-slate-200 font-medium">{typeof v === 'number' ? v.toFixed(1) : v}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* SHAP factors */}
              {prob?.shap_factors?.length > 0 && (
                <div className="mt-4 space-y-2">
                  <div className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Feature Impact (SHAP)</div>
                  {prob.shap_factors.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="text-slate-400 w-28 truncate">{f.feature}</span>
                      <div className="flex-1 bg-slate-700 rounded-full h-1.5">
                        <div
                          className={f.value >= 0 ? 'bg-blue-500 h-1.5 rounded-full' : 'bg-orange-500 h-1.5 rounded-full'}
                          style={{width: `${Math.min(Math.abs(f.value) * 100, 100)}%`}}
                        />
                      </div>
                      <span className={f.value >= 0 ? 'text-blue-400 w-12 text-right' : 'text-orange-400 w-12 text-right'}>
                        {f.value >= 0 ? '+' : ''}{f.value.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-6 p-3 bg-orange-500/10 border border-orange-500/30 rounded-xl text-center">
                <div className="text-xs text-slate-400 mb-1">Next Launch Window</div>
                <div className="text-orange-400 font-bold text-lg">
                  {countdown.days}d {countdown.hours}h {countdown.minutes}m
                </div>
              </div>
            </>
          )}
        </GlassPanel>
      </div>

      {/* Launch Schedule Table */}
      <div className="lg:col-span-7">
        <GlassPanel className="p-0 h-full flex flex-col">
          <div className="px-6 py-5 border-b border-slate-700/50 bg-[#1e2436]/50 flex justify-between items-center">
            <h3 className="font-display font-bold text-lg text-white">📅 LAUNCH SCHEDULE</h3>
            {schedule?.next_mission && (
              <div className="text-xs text-slate-400">
                Next: <span className="text-orange-400 font-bold">{schedule.next_mission.mission}</span>
              </div>
            )}
          </div>

          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <div className="w-10 h-10 border-4 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
              </div>
            ) : (
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-[#0e121e]/80 text-xs uppercase tracking-wider text-slate-500 border-b border-slate-700/50">
                  <tr>
                    <th className="px-6 py-4 font-bold">Mission</th>
                    <th className="px-6 py-4 font-bold">Vehicle</th>
                    <th className="px-6 py-4 font-bold">Date</th>
                    <th className="px-6 py-4 font-bold">Success</th>
                    <th className="px-6 py-4 font-bold">Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {launches.length > 0 ? launches.slice(0, 10).map((row, i) => (
                    <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-6 py-4 font-medium text-white">{row.mission ?? row.name ?? '—'}</td>
                      <td className="px-6 py-4 text-slate-400">{row.vehicle ?? '—'}</td>
                      <td className="px-6 py-4 text-slate-400 whitespace-nowrap">{row.date ?? '—'}</td>
                      <td className="px-6 py-4">
                        <span className={cn(
                          'inline-block px-2 py-0.5 rounded text-[10px] font-bold border uppercase',
                          row.success === true || row.success === 1
                            ? 'bg-emerald-900/40 text-emerald-400 border-emerald-500/30'
                            : row.success === false || row.success === 0
                            ? 'bg-red-900/40 text-red-400 border-red-500/30'
                            : 'bg-slate-800 text-slate-400 border-slate-600'
                        )}>
                          {row.success === true || row.success === 1 ? 'Success' : row.success === false || row.success === 0 ? 'Failed' : 'TBD'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500">{row.outcome ?? row.notes ?? '—'}</td>
                    </tr>
                  )) : (
                    <tr>
                      <td className="px-6 py-6 text-slate-400" colSpan={5}>No live launch schedule data is available.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </GlassPanel>
      </div>

    </motion.div>
  )
}

// ── Main export ──────────────────────────────────────────────────
export default function IsroMissionCenter() {
  const tabs = [
    { value: 'satellites',  label: '🛰️ Satellites' },
    { value: 'launches',    label: '🚀 Launches' },
  ]
  const [activeTab, setActiveTab] = useState('satellites')

  return (
    <div className="min-h-screen bg-[#0a0e17] text-slate-200 font-body">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-8 py-8">
        
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-2">
            <div className="w-10 h-10 rounded-full bg-orange-500 text-white flex items-center justify-center font-bold text-xl shadow-[0_0_15px_rgba(249,115,22,0.5)]">🇮🇳</div>
            <h1 className="text-3xl font-display font-bold text-white tracking-wide">ISRO Mission Center</h1>
          </div>
          <p className="text-slate-400">Track India's space assets, lunar missions, and upcoming launches in real-time.</p>
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
                  isActive ? "text-orange-400" : "text-slate-400 hover:text-slate-200"
                )}
              >
                {t.label}
                {isActive && (
                  <motion.div
                    layoutId="isroTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-400 shadow-[0_0_15px_rgba(249,115,22,0.8)]"
                  />
                )}
              </button>
            )
          })}
        </div>

        <AnimatePresence mode="wait">
          {activeTab === 'satellites'  && <SatellitesTab  key="satellites" />}
          {activeTab === 'launches'    && <LaunchesTab    key="launches" />}
        </AnimatePresence>

      </div>
    </div>
  )
}
