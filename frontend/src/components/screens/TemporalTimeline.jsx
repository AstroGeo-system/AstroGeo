'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

export default function TemporalTimeline() {
  const [activeView, setActiveView] = useState('timeline')

  return (
    <div className="min-h-screen bg-[#0e121e] text-slate-200 font-body p-8 sm:p-12">
      <div className="max-w-4xl mx-auto">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-12">
          <h1 className="text-2xl font-bold text-white tracking-wide">Temporal Change Detection</h1>
          
          {/* Toggles */}
          <div className="flex bg-[#111827]/80 rounded-xl p-1 shadow-[0_4px_15px_rgba(0,0,0,0.3)] border border-slate-700/50">
            <button
              onClick={() => setActiveView('timeline')}
              className={cn(
                "px-5 py-2 text-sm font-medium rounded-lg transition-colors",
                activeView === 'timeline' 
                  ? "bg-[#1e293b] text-indigo-400 border border-indigo-500/30 shadow-[0_0_10px_rgba(99,102,241,0.2)]"
                  : "text-slate-400 hover:text-white"
              )}
            >
              Timeline
            </button>
            <button
              onClick={() => setActiveView('graph')}
              className={cn(
                "px-5 py-2 text-sm font-medium rounded-lg transition-colors",
                activeView === 'graph' 
                  ? "bg-[#1e293b] text-indigo-400 border border-indigo-500/30 shadow-[0_0_10px_rgba(99,102,241,0.2)]"
                  : "text-slate-400 hover:text-white"
              )}
            >
              Graph
            </button>
            <button
              onClick={() => setActiveView('map')}
              className={cn(
                "px-5 py-2 text-sm font-medium rounded-lg transition-colors",
                activeView === 'map' 
                  ? "bg-[#1e293b] text-indigo-400 border border-indigo-500/30 shadow-[0_0_10px_rgba(99,102,241,0.2)]"
                  : "text-slate-400 hover:text-white"
              )}
            >
              Map
            </button>
          </div>
        </div>

        {/* Timeline body */}
        <div className="relative pl-6 sm:pl-8 space-y-8">
          {/* Vertical line connecting nodes */}
          <div className="absolute top-3 bottom-0 left-0 w-0.5 bg-indigo-500/50 shadow-[0_0_8px_rgba(99,102,241,0.8)]" />

          {/* Node 1 */}
          <motion.div initial={{opacity:0, y:-10}} animate={{opacity:1, y:0}} transition={{duration:0.3}} className="relative">
            {/* Dot */}
            <div className="absolute -left-[29px] sm:-left-[39px] top-6 w-4 h-4 rounded-full bg-indigo-500 border-2 border-[#0e121e] shadow-[0_0_12px_rgba(99,102,241,0.9)]" />
            
            <div className="bg-[#111827]/80 backdrop-blur-md rounded-2xl border border-white/5 p-6 hover:border-indigo-500/30 transition-colors shadow-lg">
              <div className="text-sm font-semibold text-indigo-400 tracking-wide mb-2">January 2020</div>
              <div className="flex items-center gap-3 mb-3">
                <h3 className="text-lg font-bold text-white tracking-wide">Baseline: Thane Vegetation Survey</h3>
                <span className="bg-slate-800 text-slate-300 text-[11px] px-2 py-0.5 rounded border border-slate-700">Claude content</span>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed font-light">
                Initial NDVI measurement: 0.68 (Healthy vegetation). Cloud-free Sentinel-2 imagery captured. Region classified as 42% green cover.
              </p>
            </div>
          </motion.div>

          {/* Node 2 */}
          <motion.div initial={{opacity:0, y:-10}} animate={{opacity:1, y:0}} transition={{duration:0.3, delay: 0.1}} className="relative">
            {/* Dot */}
            <div className="absolute -left-[29px] sm:-left-[39px] top-6 w-4 h-4 rounded-full bg-indigo-500 border-2 border-[#0e121e] shadow-[0_0_12px_rgba(99,102,241,0.9)]" />
            
            <div className="bg-[#111827]/80 backdrop-blur-md rounded-2xl border border-white/5 p-6 hover:border-indigo-500/30 transition-colors shadow-lg">
              <div className="text-sm font-semibold text-indigo-400 tracking-wide mb-2">June 2021</div>
              <div className="flex items-center gap-3 mb-3">
                <h3 className="text-lg font-bold text-white tracking-wide">Urban Expansion Detected</h3>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed font-light">
                NDVI dropped to 0.61 (-10.3%). GraphRAG correlation identified 3.2 km² of green space converted to urban infrastructure. Temperature anomaly: +1.2°C local increase.
              </p>
            </div>
          </motion.div>

          {/* Node 3 */}
          <motion.div initial={{opacity:0, y:-10}} animate={{opacity:1, y:0}} transition={{duration:0.3, delay: 0.2}} className="relative">
            {/* Dot */}
            <div className="absolute -left-[29px] sm:-left-[39px] top-6 w-4 h-4 rounded-full bg-indigo-500 border-2 border-[#0e121e] shadow-[0_0_12px_rgba(99,102,241,0.9)]" />
            
            <div className="bg-[#111827]/80 backdrop-blur-md rounded-2xl border border-white/5 p-6 hover:border-indigo-500/30 transition-colors shadow-lg">
              <div className="text-sm font-semibold text-indigo-400 tracking-wide mb-2">March 2023</div>
              <div className="flex items-center gap-3 mb-3">
                <h3 className="text-lg font-bold text-white tracking-wide">Drought Impact Assessment</h3>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed font-light">
                Soil moisture 34% below 10-year average. NDVI further declined to 0.54. Cross-referenced with NASA POWER data showing 22% rainfall deficit.
              </p>
            </div>
          </motion.div>

          {/* Node 4 */}
          <motion.div initial={{opacity:0, y:-10}} animate={{opacity:1, y:0}} transition={{duration:0.3, delay: 0.3}} className="relative">
            {/* Dot */}
            <div className="absolute -left-[29px] sm:-left-[39px] top-6 w-4 h-4 rounded-full bg-indigo-500 border-2 border-[#0e121e] shadow-[0_0_12px_rgba(99,102,241,0.9)]" />
            
            <div className="bg-[#111827]/80 backdrop-blur-md rounded-2xl border border-white/5 p-6 hover:border-indigo-500/30 transition-colors shadow-lg">
              <div className="text-sm font-semibold text-indigo-400 tracking-wide mb-2">December 2024</div>
              <div className="flex items-center gap-3 mb-3">
                <h3 className="text-lg font-bold text-white tracking-wide">Current State: Stabilization</h3>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed font-light">
                Afforestation efforts visible in satellite imagery (+4% NDVI recovery in designated zones). Soil moisture normalized.
              </p>
            </div>
          </motion.div>

        </div>
      </div>
    </div>
  )
}
