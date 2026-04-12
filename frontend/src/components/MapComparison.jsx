import { useState } from 'react'

export default function MapComparison() {
  const [slider, setSlider] = useState(50)

  return (
    <div className="glass-panel overflow-hidden rounded-xl">
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <h3 className="font-display font-semibold text-accent-cyan">Map Comparison</h3>
        <div className="flex gap-4 text-sm">
          <span className="text-slate-400">2016</span>
          <span className="text-slate-400">2023</span>
        </div>
      </div>
      <div className="relative h-80 bg-space-700">
        {/* Placeholder map layers - 2016 left, 2023 right */}
        <div
          className="absolute inset-0 bg-gradient-to-br from-emerald-900/40 to-space-800"
          style={{ clipPath: `inset(0 ${100 - slider}% 0 0)` }}
        />
        <div
          className="absolute inset-0 bg-gradient-to-br from-cyan-900/40 to-space-800"
          style={{ clipPath: `inset(0 0 0 ${slider}%)` }}
        />
        {/* Grid overlay */}
        <div
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `
              linear-gradient(rgba(0,212,255,0.3) 1px, transparent 1px),
              linear-gradient(90deg, rgba(0,212,255,0.3) 1px, transparent 1px)
            `,
            backgroundSize: '24px 24px',
          }}
        />
        {/* Slider divider */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-accent-cyan z-10 pointer-events-none flex items-center justify-center"
          style={{ left: `${slider}%` }}
        >
          <span className="absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-10 rounded bg-accent-cyan/90 flex items-center justify-center text-space-900 text-xs font-bold shadow-glow">
            ⇄
          </span>
        </div>
        <div className="absolute bottom-4 left-4 right-4 flex justify-between text-xs text-slate-500">
          <span>2016 satellite imagery</span>
          <span>2023 satellite imagery</span>
        </div>
      </div>
      <div className="p-3 border-t border-white/10 flex items-center gap-4">
        <input
          type="range"
          min="0"
          max="100"
          value={slider}
          onChange={(e) => setSlider(Number(e.target.value))}
          className="flex-1 h-2 rounded-full appearance-none bg-white/10 accent-accent-cyan"
        />
        <span className="text-accent-cyan font-mono text-sm w-12">{slider}%</span>
      </div>
    </div>
  )
}
