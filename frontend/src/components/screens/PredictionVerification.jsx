'use client'

import { useMemo, useState } from 'react'
import GlassCard from '@/components/ui/GlassCard'
import TabsUnderline from '@/components/ui/TabsUnderline'
import Badge from '@/components/ui/Badge'
import { Field } from '@/components/ui/Field'
import { motion } from 'framer-motion'

function CopyIcon() {
  return (
    <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-white/5 border border-white/10 text-slate-300">
      ⧉
    </span>
  )
}

export default function PredictionVerification() {
  const tabs = useMemo(
    () => [
      { value: 'verify', label: 'Verify Predictions' },
      { value: 'cards', label: 'Model Cards' },
      { value: 'audit', label: 'Audit Log' },
    ],
    []
  )
  const [activeTab, setActiveTab] = useState('verify')

  const predictions = [
    { title: 'Weather Prediction', model: 'Satellite Model', status: 'Verified' },
    { title: 'Flood Prediction', model: 'Satellite Model', status: 'Pending' },
    { title: 'Deforestation Prediction', model: 'Satellite Model', status: 'Verified' },
    { title: 'Drought Prediction', model: 'Satellite Model', status: 'Needs Review' },
  ]

  const steps = [
    { title: 'Data Retrieval', subtitle: '(Satellite)' },
    { title: 'Model Processing', subtitle: '(AI Analysis)' },
    { title: 'Output Comparison', subtitle: '' },
    { title: 'Validation', subtitle: '' },
  ]

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      <TabsUnderline tabs={tabs} active={activeTab} onChange={setActiveTab} />

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT SIDEBAR */}
        <div className="lg:col-span-4 space-y-4">
          <GlassCard className="p-4">
            <div className="text-xs text-slate-400 mb-2">Enter Prediction ID</div>
            <div className="flex items-center gap-2 rounded-2xl bg-white/5 border border-white/10 px-3 py-2">
              <span className="text-slate-500">⌕</span>
              <input
                className="w-full bg-transparent outline-none text-sm text-slate-200 placeholder:text-slate-600"
                placeholder="Enter Prediction ID"
              />
            </div>
          </GlassCard>

          <div className="space-y-3">
            {predictions.map((p, idx) => (
              <GlassCard key={idx} className="p-4" animate={false}>
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm text-slate-100 font-medium truncate">
                      {p.title}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">{p.model}</div>
                  </div>
                  <Badge
                    tone={
                      p.status === 'Verified'
                        ? 'green'
                        : p.status === 'Pending'
                        ? 'amber'
                        : 'red'
                    }
                  >
                    {p.status}
                  </Badge>
                </div>
              </GlassCard>
            ))}
          </div>
        </div>

        {/* RIGHT MAIN */}
        <div className="lg:col-span-8 space-y-6">
          <GlassCard className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-display text-lg text-slate-100">
                  Verification Results
                </div>
                <div className="text-sm text-slate-400 mt-1 max-w-2xl">
                  Predictions are verified using satellite evidence, consensus checks, and
                  cross-model agreement to ensure reliable outcomes.
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-slate-500">Verification Status</div>
                <div className="mt-1">
                  <Badge tone="green">Verified</Badge>
                </div>
              </div>
            </div>
          </GlassCard>

          <GlassCard className="p-5">
            <div className="font-display text-sm text-slate-100">Orphan Hash Proof</div>
            <div className="mt-4 space-y-3">
              {[
                'c4f0e3f2d61c9a4b7f3c0a1d92d3a0b8f1a9d2c3b4e5f6a7b8c9d0e1f2a3b4c5',
                '0a2b9f1e4d6c8b7a9e0f1d2c3b4a59687766554433221100ffeeddccbbaa9988',
              ].map((h) => (
                <div
                  key={h}
                  className="flex items-center gap-3 rounded-2xl bg-[#0b1224]/70 border border-white/10 px-4 py-3"
                >
                  <code className="text-xs text-slate-300 break-all flex-1">{h}</code>
                  <CopyIcon />
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard className="p-5">
            <div className="font-display text-sm text-slate-100">Evidence Chain</div>
            <div className="mt-5 overflow-x-auto">
              <div className="min-w-[720px] flex items-center gap-4">
                {steps.map((s, i) => (
                  <div key={s.title} className="flex items-center gap-4">
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.08 * i, duration: 0.35 }}
                      className="rounded-2xl bg-white/5 border border-white/10 px-4 py-3 w-[170px]"
                    >
                      <div className="text-sm text-slate-100 font-medium">
                        {s.title}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {s.subtitle}
                      </div>
                    </motion.div>
                    {i !== steps.length - 1 && (
                      <div className="text-slate-600">→</div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
                <Field label="Evidence sources" value="Sentinel‑2, IRS, Weather grids" />
              </div>
              <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
                <Field label="Consensus" value="3/3 models agree" accent />
              </div>
              <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
                <Field label="Confidence" value="0.93" accent />
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  )
}

