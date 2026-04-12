'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import dynamic from 'next/dynamic'
import { api } from '@/lib/api'

const GlobeHero = dynamic(
  () => import('@/components/GlobeHero'),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full w-full">
        <div className="text-slate-500 text-sm animate-pulse">Loading globe...</div>
      </div>
    ),
  }
)

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

function GlassPanel({ children, className }) {
  return (
    <div className={cn("bg-[#111827]/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl", className)}>
      {children}
    </div>
  )
}

function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-800 mb-6">
      <div className="flex gap-16 px-8">
        {tabs.map(t => {
          const isActive = active === t.value
          return (
            <button
              key={t.value}
              onClick={() => onChange(t.value)}
              className={cn(
                "relative pb-4 text-lg font-medium tracking-wide transition-colors",
                isActive ? "text-cyan-400" : "text-slate-300 hover:text-white"
              )}
            >
              {t.label}
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.8)]"
                />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function Toggle({ checked, onChange, label }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <span className="text-sm font-medium text-slate-300">{label}</span>
      <div className={`relative w-10 h-5 md:w-11 md:h-6 rounded-full transition-colors ${checked ? 'bg-cyan-500/40 border border-cyan-400/50' : 'bg-slate-700'}`}>
        <div className={`absolute top-0.5 bottom-0.5 w-4 md:w-5 bg-cyan-300 rounded-full transition-transform ${checked ? 'translate-x-5 md:translate-x-5 shadow-[0_0_10px_rgba(34,211,238,0.8)]' : 'translate-x-0.5 bg-slate-400'}`} />
      </div>
      <input type="checkbox" className="sr-only" checked={checked} onChange={onChange} />
    </label>
  )
}

function qualityLabel(elev) {
  if (elev >= 60) return { label: 'EXCELLENT', cls: 'bg-emerald-900/40 text-emerald-400 border border-emerald-500/30' }
  if (elev >= 30) return { label: 'GOOD',      cls: 'bg-cyan-900/40 text-cyan-400 border border-cyan-500/30' }
  return              { label: 'LOW',       cls: 'bg-amber-900/40 text-amber-500 border border-amber-500/30' }
}

export default function EarthMonitoringDashboard() {
  const tabs = [
    { value: 'satellites', label: 'Satellites' },
    { value: 'asteroids', label: 'Asteroids' },
    { value: 'launches', label: 'Launches' },
    { value: 'sun', label: 'Sun' }
  ]
  const [activeTab, setActiveTab] = useState('satellites')
  const [nightMode, setNightMode] = useState(true)
  const [passes,   setPasses]     = useState([])
  const [issInfo,  setIssInfo]    = useState(null)

  useEffect(() => {
    api.getISSPasses().then(data => {
      if (!data?.length) return
      setPasses(data.slice(0, 3))
      setIssInfo(data[0])
    })
  }, [])

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />
      
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start h-[calc(100vh-140px)] min-h-[600px]">
        
        {/* LEFT Globe Area */}
        <div className="lg:col-span-8 h-full relative group">
          <GlassPanel className="h-full w-full p-2 relative overflow-hidden flex flex-col justify-center items-center">
            {/* Top Right Toggle */}
            <div className="absolute top-6 right-6 z-10">
              <Toggle checked={nightMode} onChange={(e) => setNightMode(e.target.checked)} label="Night Mode" />
            </div>

            {/* Simulated globe component taking space */}
            <div className="absolute inset-0 z-0 flex items-center justify-center">
               <GlobeHero />
            </div>

            {/* Legend Bottom Left */}
            <div className="absolute bottom-6 left-6 z-10">
              <div className="space-y-3">
                <h4 className="font-display font-semibold text-white tracking-wide">Legend</h4>
                <div className="space-y-2 text-sm text-slate-300">
                  <div className="flex items-center gap-3"><div className="w-3.5 h-3.5 rounded bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.8)]"/> Telemetry</div>
                  <div className="flex items-center gap-3"><div className="w-3.5 h-3.5 rounded bg-slate-500 shadow-[0_0_10px_rgba(100,116,139,0.8)]"/> Debris</div>
                  <div className="flex items-center gap-3"><div className="w-3.5 h-3.5 rounded bg-orange-500 shadow-[0_0_10px_rgba(249,115,22,0.8)]"/> Phenovator</div>
                  <div className="flex items-center gap-3"><div className="w-3.5 h-3.5 rounded bg-cyan-700 shadow-[0_0_10px_rgba(14,116,144,0.8)]"/> Singularity</div>
                </div>
              </div>
            </div>

            {/* Slider Bottom Right */}
            <div className="absolute bottom-8 right-8 z-10 flex gap-2 items-center bg-slate-900/50 backdrop-blur-md rounded-full px-4 py-2 border border-slate-700">
               <div className="w-24 h-1 bg-slate-700 rounded-full relative">
                 <div className="absolute top-0 left-0 bottom-0 w-[60%] bg-cyan-400 rounded-full shadow-[0_0_10px_rgba(34,211,238,0.8)]" />
                 <div className="absolute top-[50%] left-[60%] -translate-x-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-white rounded-full shadow-lg" />
               </div>
            </div>
          </GlassPanel>
        </div>

        {/* RIGHT Side Panels */}
        <div className="lg:col-span-4 h-full flex flex-col gap-6">
          
          <GlassPanel className="p-6">
            <h3 className="font-display font-semibold text-lg text-white mb-4 tracking-wide">Satellite Quick Info</h3>
            <div className="space-y-2">
               <div className="text-cyan-400 font-semibold mb-3">ISS (ZARYA)</div>
               <div className="flex justify-between text-sm"><span className="text-slate-400">Altitude</span> <span className="text-slate-200">408 km</span></div>
               <div className="flex justify-between text-sm"><span className="text-slate-400">Velocity</span> <span className="text-slate-200">7.66 km/s</span></div>
               <div className="flex justify-between text-sm"><span className="text-slate-400">Current Location</span> <span className="text-slate-200">Over India</span></div>
               <div className="flex justify-between flex-col gap-1 mt-4 text-sm border-t border-slate-800 pt-3">
                 <span className="text-slate-400">Upcoming Passes:</span>
                 {issInfo ? (
                   <span className="text-slate-200 text-right pr-2">
                     {new Date(issInfo.risetime * 1000).toLocaleString('en-IN', {
                       timeZone: 'Asia/Kolkata', month: 'short',
                       day: 'numeric', hour: '2-digit', minute: '2-digit',
                     })} IST<br/>
                     {issInfo.duration}s · {issInfo.maxelevation ?? issInfo.max_el}° max elevation
                   </span>
                 ) : (
                   <span className="text-slate-200 text-right pr-2">Jan 30, 8:42 PM,<br/>5 min, 40° Elevation</span>
                 )}
               </div>
            </div>
          </GlassPanel>

          <GlassPanel className="p-6 flex-1 flex flex-col">
            <h3 className="font-display font-semibold text-lg text-white mb-4 tracking-wide">Satellite Pass Predictor</h3>
            
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <label className="text-xs text-slate-500 mb-1.5 block">Location</label>
                <select className="w-full bg-slate-900/50 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-2 outline-none focus:border-cyan-500/50 appearance-none">
                  <option>Location ⌄</option>
                  <option>Pune, India</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500 mb-1.5 block">Satellite</label>
                <select className="w-full bg-slate-900/50 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-2 outline-none focus:border-cyan-500/50 appearance-none">
                  <option>Date Range ⌄</option>
                  <option>Next 7 Days</option>
                </select>
              </div>
            </div>

            <div className="flex justify-between text-xs text-slate-500 mb-3 uppercase tracking-wider font-semibold">
              <span>Recent Passes</span>
              <span>Results</span>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto pr-2">
              {passes.length > 0 ? passes.map((p, i) => {
                const elev = p.maxelevation ?? p.max_el ?? 30
                const q    = qualityLabel(elev)
                const time = new Date(p.risetime * 1000).toLocaleString('en-IN', {
                  timeZone: 'Asia/Kolkata', month: 'short',
                  day: 'numeric', hour: '2-digit', minute: '2-digit',
                })
                return (
                  <div key={i} className="flex justify-between items-center p-3 rounded-xl bg-slate-800/30 border border-slate-700/50">
                    <div>
                      <div className="text-sm font-semibold text-slate-200">{time} IST</div>
                      <div className="text-xs text-slate-500">Max ELEV: {elev}°</div>
                    </div>
                    <div className="text-right">
                      <div className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${q.cls}`}>{q.label}</div>
                    </div>
                  </div>
                )
              }) : (
                // Fallback static cards while loading
                <>
                  <div className="flex justify-between items-center p-3 rounded-xl bg-slate-800/30 border border-slate-700/50">
                    <div>
                      <div className="text-sm font-semibold text-slate-200">Jan 30, 8:42 PM</div>
                      <div className="text-xs text-slate-500">Max ELEV: 60° 8:45 PM</div>
                    </div>
                    <div className="text-right">
                      <div className="inline-block px-2 py-0.5 rounded text-xs font-bold bg-emerald-900/40 text-emerald-400 border border-emerald-500/30">EXCELLENT</div>
                      <div className="text-xs text-slate-500 mt-1">A Conditions given</div>
                    </div>
                  </div>
                  <div className="flex justify-between items-center p-3 rounded-xl bg-slate-800/30 border border-slate-700/50">
                    <div>
                      <div className="text-sm font-semibold text-slate-200">Jan 31, 8:15 PM</div>
                      <div className="text-xs text-slate-500">Max ELEV: 22° 8:18 PM</div>
                    </div>
                    <div className="text-right">
                      <div className="inline-block px-2 py-0.5 rounded text-xs font-bold bg-amber-900/40 text-amber-500 border border-amber-500/30">LOW</div>
                      <div className="text-xs text-slate-500 mt-1">B Conditions given</div>
                    </div>
                  </div>
                </>
              )}
            </div>

          </GlassPanel>

        </div>
      </div>
    </div>
  )
}
