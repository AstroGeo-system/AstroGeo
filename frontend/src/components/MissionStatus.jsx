import { chandrayaan3Mission } from '../data/placeholderData'

export default function MissionStatus() {
  const { name, status, phase, lander, rover, telemetry, progress } = chandrayaan3Mission

  return (
    <div className="glass-panel h-full flex flex-col overflow-hidden">
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <h3 className="font-display font-semibold text-accent-cyan tracking-wide">
            Mission Monitoring
          </h3>
          <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-medium">
            {status}
          </span>
        </div>
        <p className="text-slate-400 text-sm mt-1">{name} • {phase}</p>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-4">
        {/* Progress */}
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-slate-400">Mission progress</span>
            <span className="text-accent-cyan font-mono">{progress}%</span>
          </div>
          <div className="h-2 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-accent-cyan to-accent-blue transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Lander */}
        <div className="rounded-lg bg-white/5 border border-white/10 p-3">
          <h4 className="text-slate-300 font-medium text-sm flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Lander — {lander.name}
          </h4>
          <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
            <div><span className="text-slate-500">Status</span><p className="text-slate-200">{lander.status}</p></div>
            <div><span className="text-slate-500">Temp</span><p className="text-slate-200">{lander.temp}</p></div>
            <div><span className="text-slate-500">Power</span><p className="text-accent-cyan">{lander.power}</p></div>
            <div><span className="text-slate-500">Last contact</span><p className="text-slate-200">{lander.lastContact}</p></div>
          </div>
        </div>

        {/* Rover */}
        <div className="rounded-lg bg-white/5 border border-white/10 p-3">
          <h4 className="text-slate-300 font-medium text-sm flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Rover — {rover.name}
          </h4>
          <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
            <div><span className="text-slate-500">Status</span><p className="text-slate-200">{rover.status}</p></div>
            <div><span className="text-slate-500">Distance</span><p className="text-slate-200">{rover.distance}</p></div>
            <div><span className="text-slate-500">Samples</span><p className="text-accent-cyan">{rover.samples}</p></div>
            <div><span className="text-slate-500">Last contact</span><p className="text-slate-200">{rover.lastContact}</p></div>
          </div>
        </div>

        {/* Telemetry */}
        <div>
          <h4 className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">Telemetry</h4>
          <div className="space-y-2">
            {telemetry.map((t, i) => (
              <div key={i} className="flex justify-between text-sm py-1 border-b border-white/5 last:border-0">
                <span className="text-slate-500">{t.label}</span>
                <span className="text-slate-200 font-mono">{t.value}{t.unit}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
