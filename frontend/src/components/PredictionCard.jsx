import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'
import { orbitalPredictions, chartData } from '../data/placeholderData'

export default function PredictionCard() {
  return (
    <div className="glass-panel glass-panel-hover p-5 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-lg">📡</span>
        <h3 className="font-display font-semibold text-accent-cyan tracking-wide">
          Orbital Predictions
        </h3>
      </div>
      <div className="flex-1 min-h-[120px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="predGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00d4ff" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#00d4ff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} />
            <YAxis hide />
            <Tooltip
              contentStyle={{
                background: 'rgba(15, 22, 41, 0.95)',
                border: '1px solid rgba(0, 212, 255, 0.3)',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#00d4ff"
              strokeWidth={2}
              fill="url(#predGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="grid grid-cols-4 gap-2 mt-2">
        {orbitalPredictions.map((p, i) => (
          <div key={i} className="text-center py-1 rounded bg-white/5">
            <p className="text-xs text-slate-400">{p.time}</p>
            <p className="text-accent-cyan font-medium text-sm">{p.elevation}°</p>
          </div>
        ))}
      </div>
    </div>
  )
}
