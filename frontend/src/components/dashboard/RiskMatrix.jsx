'use client'

import React from 'react'

const RiskMatrix = ({ data }) => {
  if (!data || !data.data || !data.x_axis || !data.y_axis) {
    return (
      <div className="h-64 flex items-center justify-center border border-dashed border-slate-700 rounded-xl">
        <p className="text-slate-500 text-sm">No matrix data available</p>
      </div>
    )
  }

  const { x_axis, y_axis, data: matrix, title, description } = data

  const getRiskColor = (val) => {
    if (val < 25) return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
    if (val < 50) return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30'
    if (val < 75) return 'bg-orange-500/20 text-orange-500 border-orange-500/30'
    return 'bg-rose-500/20 text-rose-500 border-rose-500/30'
  }

  const getRiskLabel = (val) => {
    if (val < 25) return 'LOW RISK'
    if (val < 50) return 'MOD RISK'
    if (val < 75) return 'HIGH RISK'
    return 'CRITICAL'
  }

  return (
    <div className="w-full space-y-6">
      <div>
        <h3 className="text-xl font-display font-bold text-white mb-2">{title}</h3>
        <p className="text-sm text-slate-400 max-w-2xl">{description}</p>
      </div>

      <div className="flex gap-4 mb-8">
        {[
          { label: 'AXES', val: `${y_axis.label} × ${x_axis.label}` },
          { label: 'CELL VALUE', val: 'Avg. predicted risk score (0-100)' },
          { label: 'CLINICAL USE', val: 'Research Lab Priority Routing' },
          { label: 'CRITICAL THRESHOLD', val: '>75 = immediate escalation', highlight: true }
        ].map((stat, i) => (
          <div key={i} className="bg-slate-900/50 border border-white/5 rounded-lg p-3 flex-1">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">{stat.label}</div>
            <div className={`text-xs font-medium ${stat.highlight ? 'text-rose-400' : 'text-slate-200'}`}>{stat.val}</div>
          </div>
        ))}
      </div>

      <div className="relative overflow-x-auto custom-scrollbar pb-4">
        {/* Y-axis label (vertical) */}
        <div className="absolute left-0 top-1/2 -translate-y-1/2 -rotate-90 origin-left text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em] whitespace-nowrap ml-2">
          ← {y_axis.label} →
        </div>

        <div className="ml-12 min-w-[600px]">
          {/* X-axis labels */}
          <div className="flex justify-center mb-6">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em]">
              ← {x_axis.label} →
            </div>
          </div>

          <div className="grid grid-cols-[100px_repeat(5,1fr)] gap-3">
            {/* Legend for X axis ticks */}
            <div />
            {x_axis.ticks.map((tick, i) => (
              <div key={i} className="text-[10px] font-bold text-slate-500 text-center uppercase truncate">
                {tick}
              </div>
            ))}

            {/* Matrix Rows */}
            {matrix.map((row, i) => (
              <React.Fragment key={i}>
                {/* Y-axis tick */}
                <div className="flex items-center justify-end pr-4">
                  <span className="text-[10px] font-bold text-slate-500 uppercase text-right leading-tight">
                    {y_axis.ticks[i]}
                  </span>
                </div>

                {/* Data Cells */}
                {row && row.map((val, j) => (
                  <div 
                    key={j} 
                    className={`h-24 rounded-xl border flex flex-col items-center justify-center transition-all hover:scale-[1.02] cursor-default shadow-lg group ${getRiskColor(val)}`}
                  >

                    <div className="text-2xl font-bold font-mono tracking-tighter mb-1">{val}</div>
                    <div className="text-[9px] font-black uppercase tracking-widest opacity-80">{getRiskLabel(val)}</div>
                    <div className="w-8 h-1 rounded-full bg-current opacity-20 mt-3 group-hover:opacity-40 transition-opacity" />
                  </div>
                ))}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-slate-900/40 rounded-xl p-4 border border-slate-800/50 flex items-center justify-between">
        <div className="text-xs text-slate-400">
           The heat intensity represents the combined probability of high-risk outcomes.
        </div>
        <div className="flex items-center gap-6">
           <div className="flex items-center gap-2">
             <div className="w-3 h-3 rounded bg-emerald-500/20 border border-emerald-500/40" />
             <span className="text-[10px] text-slate-500 font-bold">LOW</span>
           </div>
           <div className="flex items-center gap-2">
             <div className="w-3 h-3 rounded bg-rose-500/20 border border-rose-500/40" />
             <span className="text-[10px] text-slate-500 font-bold">CRITICAL</span>
           </div>
        </div>
      </div>
    </div>
  )
}

export default RiskMatrix
