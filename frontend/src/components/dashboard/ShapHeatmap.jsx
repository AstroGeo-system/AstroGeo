'use client'

import React from 'react'

const ShapHeatmap = ({ data }) => {
  if (!data || !data.features || !data.classes || !data.values) {
    return (
      <div className="h-64 flex items-center justify-center border border-dashed border-slate-700 rounded-xl">
        <p className="text-slate-500 text-sm">No SHAP data available</p>
      </div>
    )
  }

  const { features, classes, values, title } = data

  // Find max value for normalization
  const maxVal = Math.max(...values.flat(), 0.0001)

  return (
    <div className="w-full space-y-4">
      <div className="flex justify-between items-end">
        <div>
          <h3 className="text-lg font-display font-semibold text-white">{title}</h3>
          <p className="text-xs text-slate-400">Rows: Features · Columns: Risk Classes</p>
        </div>
        <div className="flex items-center gap-4 text-[10px] font-bold uppercase tracking-widest">
           <div className="flex items-center gap-1.5">
             <div className="w-2 h-2 rounded-full bg-blue-500/20 border border-blue-500/50" />
             <span className="text-slate-500">Low Impact</span>
           </div>
           <div className="flex items-center gap-1.5">
             <div className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]" />
             <span className="text-red-400">High Impact</span>
           </div>
        </div>
      </div>

      <div className="overflow-x-auto custom-scrollbar pb-2">
        <div className="min-w-[600px]">
          {/* Header row with labels */}
          <div className="grid grid-cols-[150px_repeat(auto-fit,minmax(0,1fr))] gap-2 mb-2">
            <div />
            {classes.map((cls, i) => (
              <div key={i} className="text-[10px] font-bold text-slate-500 uppercase text-center truncate px-1">
                {cls}
              </div>
            ))}
          </div>

          {/* Rows for each feature */}
          <div className="space-y-2">
            {features.map((feat, i) => (
              <div key={i} className="grid grid-cols-[150px_repeat(auto-fit,minmax(0,1fr))] gap-2 items-center">
                <div className="text-xs font-medium text-slate-400 truncate pr-4 text-right">
                  {feat}
                </div>
                {values[i] && values[i].map((val, j) => {
                  const intensity = val / maxVal
                  return (
                    <div 
                      key={j} 
                      className="group relative h-10 rounded-md transition-all border border-white/5 hover:border-white/20"
                      style={{ 
                        backgroundColor: `rgba(239, 68, 68, ${0.1 + intensity * 0.8})`,
                        boxShadow: intensity > 0.8 ? '0 0 10px rgba(239, 68, 68, 0.2)' : 'none'
                      }}
                    >
                      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900/80 rounded-md">
                        <span className="text-[10px] font-mono font-bold text-white">{val.toFixed(3)}</span>
                      </div>
                    </div>
                  )
                })}

              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-slate-800/50">
         <div className="text-[10px] text-slate-500 flex items-center gap-2">
            <span className="text-indigo-400">ℹ</span> Every cell represents how much a feature contributed to the model's decision for that risk category.
         </div>
         <div className="flex gap-1">
            {[0, 0.2, 0.4, 0.6, 0.8, 1].map((lvl) => (
               <div key={lvl} className="w-3 h-1.5 rounded-full" style={{ backgroundColor: `rgba(239, 68, 68, ${0.1 + lvl * 0.8})` }} />
            ))}
         </div>
      </div>
    </div>
  )
}

export default ShapHeatmap
