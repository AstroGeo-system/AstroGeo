import { satellites } from '../data/placeholderData'

export default function SatelliteCard() {
  return (
    <div className="glass-panel glass-panel-hover p-5 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <h3 className="font-display font-semibold text-accent-cyan tracking-wide">
          Live Satellite Tracking
        </h3>
      </div>
      <ul className="space-y-3 flex-1 overflow-auto max-h-40">
        {satellites.slice(0, 4).map((sat) => (
          <li
            key={sat.id}
            className="flex items-center justify-between py-2 px-3 rounded-lg bg-white/5 border border-white/5 hover:border-accent-cyan/20 transition-smooth"
          >
            <div>
              <p className="font-medium text-slate-200 text-sm">{sat.name}</p>
              <p className="text-xs text-slate-500">{sat.orbit} • {sat.altitude} km</p>
            </div>
            <span className="text-xs text-slate-500">{sat.lastUpdate}</span>
          </li>
        ))}
      </ul>
      <p className="text-xs text-accent-cyan/80 mt-2">Real-time TLE updates</p>
    </div>
  )
}
