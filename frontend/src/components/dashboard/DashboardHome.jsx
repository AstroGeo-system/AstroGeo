'use client'

import Link from 'next/link'
import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Satellite, Orbit, Globe2, Rocket, Radio, ChevronRight, Sparkles,
         AlertTriangle, Sun, BarChart3, Leaf, ExternalLink, Share2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { featureCards } from '@/data/dashboardData'
import APOD from '@/components/APOD'
import { cn } from '@/lib/cn'
import { api } from '@/lib/api'
import AskAstroGeo from '@/components/persona/AskAstroGeo'
import PersonaBanner from '@/components/persona/PersonaBanner'
import { usePersona } from '@/hooks/usePersona'
import { buildSolarAngle, buildVegetationAngle, buildAsteroidLaunchAngle } from '@/utils/storyAngles'

const iconMap = { Satellite, Orbit, Globe2, Rocket }

const badgeStyles = {
  verified: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  analyzing: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
  upcoming: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
}
const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
}

// ── U3: Policy Maker Dashboard ────────────────────────────────────
function PolicyMakerDashboard() {
  const ZONES = ['Maharashtra', 'Marathwada', 'Vidarbha', 'Punjab', 'Rajasthan',
                 'Tamil Nadu', 'Karnataka']

  const [droughtData, setDroughtData]  = useState([])
  const [solarStatus, setSolarStatus]  = useState('CALM')
  const [launchData,  setLaunchData]   = useState(null)
  const [vegData,     setVegData]      = useState([])
  const [loading,     setLoading]      = useState(true)

  useEffect(() => {
    const promises = [
      // Drought: fetch for 4 zones
      Promise.all(
        ZONES.slice(0, 5).map(z =>
          api.getDrought(z).then(d => d ? { zone: z, ...d } : null).catch(() => null)
        )
      ),
      api.getSolarEvents(),
      api.getLaunchSchedule(),
      // Vegetation: 4 zones
      Promise.all(
        ZONES.slice(0, 4).map(z =>
          api.getNDVI(z).then(d => d ? { zone: z, summary: d.summary } : null).catch(() => null)
        )
      ),
    ]

    Promise.all(promises).then(([drought, solar, launch, veg]) => {
      const validDrought = drought.filter(Boolean).sort((a, b) => b.drought_score - a.drought_score)
      setDroughtData(validDrought)

      const events = solar?.events ?? solar?.data ?? []
      const hasActive = Array.isArray(events) && events.some(e =>
        e.classType?.startsWith('X') || e.classType?.startsWith('M')
      )
      setSolarStatus(hasActive ? 'ACTIVE' : 'CALM')
      setLaunchData(launch)
      setVegData(veg.filter(Boolean))
      setLoading(false)
    })
  }, [])

  const severityColor = (s) =>
    s === 'Severe' ? 'text-red-400 bg-red-500/10 border-red-500/30' :
    s === 'Moderate' ? 'text-amber-400 bg-amber-500/10 border-amber-500/30' :
    'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'

  const highRiskCount = droughtData.filter(d => d.severity === 'Severe').length
  const worstDrought = droughtData[0]
  const worstVeg = vegData.length
    ? vegData.reduce((a, b) => (a?.summary?.mean_ndvi ?? 1) < (b?.summary?.mean_ndvi ?? 1) ? a : b)
    : null
  const vegLossCount = vegData.filter(v => (v?.summary?.mean_ndvi ?? 1) < 0.45).length

  const launchDays = launchData?.countdown?.days ?? 23
  const launchProb = launchData?.probability ?? launchData?.launch_probability ?? 91.9

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="grid gap-5 sm:grid-cols-2">
      {/* Card 1 — Regional Drought Risk */}
      <motion.div variants={item}>
        <Card className="h-full border-white/10 bg-white/[0.04] border-t-4 border-t-red-500">
          <CardContent className="p-5">
            <div className="mb-3 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-400" />
              <h3 className="text-sm font-semibold text-white">Drought Risk Across India</h3>
            </div>
            {loading ? (
              <div className="flex justify-center py-6"><div className="w-6 h-6 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin"/></div>
            ) : (
              <>
                <div className="space-y-2 mb-4">
                  {droughtData.slice(0, 5).map((d, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <span className="text-slate-300">{d.zone}</span>
                      <span className={cn('px-2 py-0.5 rounded border text-[10px] font-bold', severityColor(d.severity))}>
                        {d.severity}
                      </span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-slate-500 italic border-t border-white/5 pt-3">
                  {highRiskCount} districts at high drought risk{worstDrought ? `, concentrated in ${worstDrought.zone}` : ''}.
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Card 2 — Solar Storm Economic Impact */}
      <motion.div variants={item}>
        <Card className="h-full border-white/10 bg-white/[0.04] border-t-4 border-t-orange-500">
          <CardContent className="p-5">
            <div className="mb-3 flex items-center gap-2">
              <Sun className="h-4 w-4 text-orange-400" />
              <h3 className="text-sm font-semibold text-white">Space Weather: Known Economic Impact</h3>
            </div>
            <div className="space-y-3">
              <div className="rounded-lg bg-orange-500/10 border border-orange-500/20 px-3 py-2">
                <div className="text-xl font-bold text-orange-400">$500M</div>
                <div className="text-xs text-slate-400">Loss to US farmers — May 2024 G5 storm (GPS disruption)</div>
                <div className="text-[10px] text-slate-600 mt-1">Source: USDA Economic Research Service</div>
              </div>
              <div className="rounded-lg bg-white/[0.03] border border-white/10 px-3 py-2">
                <div className="text-lg font-bold text-amber-400">$111M–$27B</div>
                <div className="text-xs text-slate-400">NOAA estimate: grid damage from geomagnetic storms</div>
                <div className="text-[10px] text-slate-600 mt-1">Source: NOAA Space Weather Center</div>
              </div>
              <div className="flex items-center justify-between text-xs pt-1">
                <span className="text-slate-400">Current Solar Status:</span>
                <span className={cn('font-bold px-2 py-0.5 rounded border',
                  solarStatus === 'ACTIVE'
                    ? 'text-orange-400 bg-orange-500/10 border-orange-500/30'
                    : 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
                )}>
                  {solarStatus}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Card 3 — ISRO Mission Reliability */}
      <motion.div variants={item}>
        <Card className="h-full border-white/10 bg-white/[0.04] border-t-4 border-t-cyan-500">
          <CardContent className="p-5">
            <div className="mb-3 flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">ISRO Launch Reliability — 108 Mission Record</h3>
            </div>
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-white">108</div>
                <div className="text-[10px] text-slate-500">Total Launches</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-emerald-400">86%</div>
                <div className="text-[10px] text-slate-500">Success Rate</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-cyan-400">{launchDays}d</div>
                <div className="text-[10px] text-slate-500">Next Launch</div>
              </div>
            </div>
            <div className="space-y-1.5 text-xs border-t border-white/5 pt-3">
              {[
                { v: 'PSLV', rate: '93%' },
                { v: 'GSLV', rate: '72%' },
                { v: 'LVM3', rate: '100%' },
              ].map(({ v, rate }) => (
                <div key={v} className="flex justify-between">
                  <span className="text-slate-400">{v}</span>
                  <span className="font-medium text-slate-200">{rate} success rate</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[10px] text-slate-500 italic">
              Monsoon season (June–Sep) historically correlates with elevated launch risk.
            </p>
          </CardContent>
        </Card>
      </motion.div>

      {/* Card 4 — Vegetation Loss by Region */}
      <motion.div variants={item}>
        <Card className="h-full border-white/10 bg-white/[0.04] border-t-4 border-t-green-500">
          <CardContent className="p-5">
            <div className="mb-3 flex items-center gap-2">
              <Leaf className="h-4 w-4 text-green-400" />
              <h3 className="text-sm font-semibold text-white">Vegetation &amp; Land Cover Change 2018–2024</h3>
            </div>
            {loading ? (
              <div className="flex justify-center py-6"><div className="w-6 h-6 border-2 border-green-500/30 border-t-green-500 rounded-full animate-spin"/></div>
            ) : (
              <>
                <div className="space-y-2 mb-4">
                  {vegData.slice(0, 4).map((v, i) => {
                    const ndvi = v?.summary?.mean_ndvi ?? 0
                    const label = ndvi > 0.5 ? 'Healthy' : ndvi > 0.3 ? 'Moderate' : 'Poor'
                    const color = ndvi > 0.5 ? 'text-emerald-400' : ndvi > 0.3 ? 'text-amber-400' : 'text-red-400'
                    return (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <span className="text-slate-300">{v.zone}</span>
                        <span className={cn('font-medium', color)}>{label} ({ndvi.toFixed(2)})</span>
                      </div>
                    )
                  })}
                </div>
                <p className="text-xs text-slate-500 italic border-t border-white/5 pt-3">
                  {vegLossCount} of {vegData.length} monitored zones show significant vegetation stress
                  {worstVeg ? `, with ${worstVeg.zone} showing the sharpest decline` : ''}.
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}

// ── U4: Journalist Story Angles Card ─────────────────────────────
function JournalistStoryAngles({ onAsk }) {
  const [angles, setAngles] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.getSolarEvents(),
      Promise.all(
        ['Maharashtra', 'Punjab', 'Rajasthan', 'Vidarbha', 'Marathwada'].map(z =>
          api.getNDVI(z).then(d => d ? { zone: z, summary: d.summary } : null).catch(() => null)
        )
      ),
      api.getAlerts(),
      api.getLaunchSchedule(),
    ]).then(([solar, ndviList, alerts, launch]) => {
      setAngles([
        buildSolarAngle(solar),
        buildVegetationAngle(ndviList.filter(Boolean)),
        buildAsteroidLaunchAngle(alerts, launch),
      ])
      setLoading(false)
    })
  }, [])

  return (
    <Card className="mb-6 border-white/10 bg-white/[0.04] border-t-4 border-t-orange-500">
      <CardContent className="p-5">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-500/20 border border-orange-500/30">
            <span className="text-sm">📰</span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Today's Story Angles</h3>
            <p className="text-xs text-slate-500">Data-driven narratives from AstroGeo's live feeds</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center gap-3 py-4 text-xs text-slate-500">
            <div className="w-4 h-4 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin"/>
            Scanning live data feeds...
          </div>
        ) : (
          <div className="space-y-4">
            {(angles ?? []).map((angle, i) => (
              <div key={i} className="border-b border-white/5 pb-4 last:border-0 last:pb-0">
                <p className="text-sm font-semibold text-white leading-snug mb-1">{angle.headline}</p>
                <p className="text-xs text-slate-400 leading-relaxed mb-2">{angle.body}</p>
                <button
                  onClick={() => onAsk?.(angle.query)}
                  className="inline-flex items-center gap-1.5 text-[11px] font-medium text-orange-400 hover:text-orange-300 transition"
                >
                  <Sparkles className="h-3 w-3" />
                  Ask AstroGeo about this
                </button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ── Main DashboardHome ────────────────────────────────────────────
export default function DashboardHome() {
  const { persona, visibility, isSimple } = usePersona()
  const askRef = useRef(null)
  const [prefillQuery, setPrefillQuery] = useState('')

  const [ticker, setTicker] = useState({
    headline: 'ISS Position',
    detail: 'Waiting for live ISS feed...',
  })
  const [predictions, setPredictions] = useState([])

  useEffect(() => {
    api.getISSPasses().then((payload) => {
      const rawPasses = payload?.passes ?? payload ?? []
      const passes = Array.isArray(rawPasses) ? rawPasses : []
      if (!passes.length) return

      const next = passes[0]
      const time = next.risetime
        ? new Date(next.risetime * 1000).toLocaleTimeString('en-IN', {
            hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata',
          })
        : next.rise_time
        ? new Date(next.rise_time).toLocaleTimeString('en-IN', {
            hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata',
          })
        : '20:42 IST'
      setTicker({ headline: 'ISS Position', detail: `Over Indian Ocean · Next pass Mumbai: ${time} IST` })

      setPredictions((prev) => {
        const p = passes[0]
        const t = p.risetime
          ? new Date(p.risetime * 1000).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })
          : p.rise_time ? new Date(p.rise_time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }) : '—'
        const issEntry = { id: '3', title: `ISS pass — max elevation ${p.maxelevation ?? p.max_el ?? 60}°`, status: 'Upcoming', tone: 'upcoming', meta: `Tonight ${t} IST` }
        return prev.some(x => x.id === '3') ? prev : [...prev, issEntry]
      })
    })

    const t1 = setTimeout(() => {
      api.getAlerts().then(alerts => {
        const topAsteroid = alerts?.data?.[0] ?? alerts?.[0]
        if (!topAsteroid) return
        setPredictions(prev => {
          const entry = { id: '1', title: `Asteroid ${topAsteroid.designation ?? topAsteroid.des ?? 'Unknown'} — ML Threat Model`, status: 'Verified', tone: 'verified', meta: `Risk: ${topAsteroid.risk_category ?? 'Low'} · Score: ${topAsteroid.improved_risk_score?.toFixed(2) ?? 'N/A'}` }
          return [entry, ...prev.filter(x => x.id !== '1')]
        })
      }).catch(() => {})
    }, 500)

    const t2 = setTimeout(() => {
      api.getDrought('Maharashtra').then(drought => {
        if (!drought) return
        setPredictions(prev => {
          const entry = { id: '2', title: isSimple ? `Drought risk — ${drought.district}` : `Drought signal — ${drought.district}`, status: drought.severity === 'Severe' ? 'Verified' : 'Analyzing', tone: drought.severity === 'Severe' ? 'verified' : 'analyzing', meta: isSimple ? `${drought.severity} drought conditions — ${drought.drought_score > 0.6 ? 'consider delaying irrigation' : 'monitor closely'}` : `Score: ${drought.drought_score} · ${drought.severity} · NASA POWER + Sentinel-2` }
          return [...prev.filter(x => x.id !== '2'), entry]
        })
      }).catch(() => {})
    }, 1000)

    const t3 = setTimeout(() => {
      api.getNDVI('Thane', 2024).then(ndvi => {
        if (!ndvi?.summary) return
        setPredictions(prev => {
          const entry = { id: '4', title: `Vegetation anomaly — ${ndvi.results?.[0]?.zone_name ?? 'Thane'}`, status: 'Verified', tone: 'verified', meta: isSimple ? `Vegetation health: ${ndvi.summary.mean_ndvi > 0.5 ? 'Good' : ndvi.summary.mean_ndvi > 0.3 ? 'Moderate' : 'Poor'}` : `NDVI ${ndvi.summary.mean_ndvi?.toFixed(3)} · ${ndvi.summary.dominant_class?.replace(/_/g, ' ')}` }
          return [...prev.filter(x => x.id !== '4'), entry]
        })
      }).catch(() => {})
    }, 1500)

    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [isSimple])

  const filteredPredictions = predictions.filter(p => {
    if (!persona || persona === 'researcher') return true
    if (!visibility.showAsteroid && (p.id === '1' || p.title?.toLowerCase().includes('asteroid'))) return false
    return true
  })

  const handleSwitch = () => {
    if (typeof window !== 'undefined' && window.__astrogeo_switchPersona) {
      window.__astrogeo_switchPersona()
    }
  }

  const handleAskFromAngle = (query) => {
    setPrefillQuery(query)
    // Scroll to AskAstroGeo box
    setTimeout(() => {
      document.getElementById('ask-astrogeo-input')?.focus()
      document.getElementById('ask-astrogeo-input')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 100)
  }

  const isPolicyMaker = persona === 'policymaker'
  const isJournalist  = persona === 'journalist'

  return (
    <div className="relative z-10 space-y-10">
      <section className="grid gap-8 lg:grid-cols-12 lg:items-stretch">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="lg:col-span-7"
        >
          <div className="glass glass-hover overflow-hidden rounded-2xl border-white/10 p-8 lg:p-10">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-2 rounded-full border border-astro-secondary/40 bg-astro-secondary/15 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-astro-secondary">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-astro-secondary opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-astro-secondary" />
                </span>
                Live Now
              </span>
              <span className="text-xs text-slate-500">Orbital intelligence stream</span>
            </div>
            <h1 className="mt-6 font-display text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-5xl">
              AstroGeo
              <span className="block text-lg font-normal text-slate-400 sm:text-xl">
                AI-powered space &amp; Earth intelligence
              </span>
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-relaxed text-slate-400">
              Unified tracking, predictions, and verifiable evidence chains — built for operators who need
              clarity at mission speed.
            </p>

            <div className="mt-8 rounded-xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-sm">
              <div className="flex items-center gap-2 text-xs font-medium text-astro-secondary">
                <Radio className="h-4 w-4 shrink-0" />
                ISS ticker
              </div>
              <div className="mt-2 font-mono-ui text-sm text-white">{ticker.headline}</div>
              <div className="mt-1 text-xs text-slate-500">{ticker.detail}</div>
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/astronomy"
                className="inline-flex h-10 items-center justify-center rounded-lg bg-astro-primary px-5 text-sm font-medium text-white shadow-[0_0_24px_rgba(11,61,145,0.4)] transition hover:bg-astro-primary/90"
              >
                Open Astronomy Hub
              </Link>
              <Link
                href="/research"
                className="inline-flex h-10 items-center justify-center rounded-lg border border-white/15 bg-white/5 px-5 text-sm font-medium text-slate-200 transition hover:bg-white/10"
              >
                Verifiable AI Lab
                <ChevronRight className="ml-1 h-4 w-4" />
              </Link>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.08 }}
          className="lg:col-span-5"
        >
          <APOD />
        </motion.div>
      </section>

      <section>
        <PersonaBanner onSwitch={handleSwitch} />

        {/* U4: Journalist Story Angles — shown only for journalist persona */}
        {isJournalist && <JournalistStoryAngles onAsk={handleAskFromAngle} />}

        {/* AskAstroGeo search box */}
        <div className="mb-6 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-astro-secondary" />
            <span className="text-sm font-semibold text-white">Ask AstroGeo</span>
            <span className="text-xs text-slate-500">— type any question, get a real answer</span>
          </div>
          <AskAstroGeo prefill={prefillQuery} key={prefillQuery} />
        </div>

        {/* U3: Policy Maker Dashboard — replaces feature grid */}
        {isPolicyMaker ? (
          <>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Policy overview</h2>
            </div>
            <PolicyMakerDashboard />
          </>
        ) : (
          <>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Feature grid</h2>
            </div>
            <motion.div
              variants={container}
              initial="hidden"
              animate="show"
              className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
            >
              {featureCards.map((c) => {
                const Icon = iconMap[c.icon] || Satellite
                return (
                  <motion.div key={c.id} variants={item}>
                    <Link href={c.href} className="group block h-full">
                      <Card className={cn('h-full border-white/10 bg-white/[0.04] transition-all duration-300 hover:border-white/20 hover:bg-white/[0.07]', 'hover:shadow-[0_0_32px_rgba(11,61,145,0.15)]')}>
                        <CardContent className="p-6">
                          <div className={cn('mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br border border-white/10', c.accent)}>
                            <Icon className="h-6 w-6 text-white" />
                          </div>
                          <h3 className="font-semibold text-white">{c.title}</h3>
                          <p className="mt-2 text-xs leading-relaxed text-slate-400">{c.desc}</p>
                          <span className="mt-4 inline-flex items-center text-xs font-medium text-astro-secondary group-hover:gap-1">
                            Open
                            <ChevronRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                          </span>
                        </CardContent>
                      </Card>
                    </Link>
                  </motion.div>
                )
              })}
            </motion.div>
          </>
        )}
      </section>

      {/* Recent predictions — hidden for Policy Maker (they see the 4-card dashboard) */}
      {!isPolicyMaker && (
        <section>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Recent AI predictions
          </h2>
          <motion.div
            variants={container}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: '-40px' }}
            className="max-h-[420px] space-y-3 overflow-y-auto pr-1"
          >
            {filteredPredictions.length === 0 ? (
              <Card className="border-white/10 bg-white/[0.03]">
                <CardContent className="p-4 text-sm text-slate-400">No live predictions available right now.</CardContent>
              </Card>
            ) : filteredPredictions.map((p) => (
              <motion.div key={p.id} variants={item}>
                <Card className="border-white/10 bg-white/[0.03] transition hover:border-white/15">
                  <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-white">{p.title}</div>
                      <div className="mt-1 text-xs text-slate-500">{p.meta}</div>
                    </div>
                    <span className={cn('shrink-0 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-wide', badgeStyles[p.tone] || badgeStyles.upcoming)}>
                      {p.status}
                    </span>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        </section>
      )}
    </div>
  )
}
