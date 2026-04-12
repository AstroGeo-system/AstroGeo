'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import dynamic from 'next/dynamic'
import SatellitePassPredictor from '@/components/SatellitePassPredictor'
import { useAppShell } from '@/components/providers/AppShellProvider'

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

const HOME_CITY_OPTIONS = ['Mumbai, MH', 'Delhi, NCR', 'Bengaluru, KA', 'Chennai, TN', 'Kolkata, WB', 'Hyderabad, TS']

function formatLatLon(lat, lon) {
  if (lat == null || lon == null || Number.isNaN(Number(lat)) || Number.isNaN(Number(lon))) return '—'
  const la = Number(lat)
  const lo = Number(lon)
  const ns = la >= 0 ? 'N' : 'S'
  const ew = lo >= 0 ? 'E' : 'W'
  return `${Math.abs(la).toFixed(4)}° ${ns}, ${Math.abs(lo).toFixed(4)}° ${ew}`
}

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

function GlassPanel({ children, className }) {
  return (
    <div className={cn("bg-[#111827]/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden", className)}>
      {children}
    </div>
  )
}

function Toggle({ checked, onChange, label }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <span className="text-sm font-medium text-slate-300">{label}</span>
      <div className={`relative w-10 h-5 md:w-11 md:h-6 rounded-full transition-colors ${checked ? 'bg-cyan-500/40 border border-cyan-400/50' : 'bg-slate-700'}`}>
        <div className={`absolute top-0.5 bottom-0.5 w-4 md:w-5 bg-cyan-300 rounded-full transition-transform ${checked ? 'translate-x-5 shadow-[0_0_10px_rgba(34,211,238,0.8)]' : 'translate-x-0.5 bg-slate-400'}`} />
      </div>
      <input type="checkbox" className="sr-only" checked={checked} onChange={onChange} />
    </label>
  )
}

// --------------------------------------------------------------------------------
// TAB CONTENTS
// --------------------------------------------------------------------------------

function SatellitesTab() {
  const { homeCity, setHomeCity } = useAppShell()
  const [nightMode, setNightMode] = useState(true)

  return (
    <>
      <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="grid grid-cols-1 gap-6 items-start h-[calc(100vh-120px)] min-h-[700px]">
        <div className="h-full relative group">
          <GlassPanel className="h-full w-full p-2 relative flex flex-col justify-center items-center rounded-3xl">
            <div className="absolute top-6 right-6 z-10">
              <Toggle checked={nightMode} onChange={(e) => setNightMode(e.target.checked)} label="Night Mode" />
            </div>
            <div className="absolute inset-0 z-0 flex items-center justify-center">
              <GlobeHero nightMode={nightMode} />
            </div>
          </GlassPanel>
        </div>
      </motion.div>
      <SatellitePassPredictor />
    </>
  )
}

/** First NEO in NASA feed `near_earth_objects` (object keyed by date). */
function pickFirstNeoFromFeed(data) {
  const buckets = data?.near_earth_objects
  if (!buckets || typeof buckets !== 'object') return null
  const dates = Object.keys(buckets).sort()
  for (const d of dates) {
    const list = buckets[d]
    if (Array.isArray(list) && list.length > 0) return { raw: list[0], ca: list[0].close_approach_data?.[0], dateKey: d }
  }
  return null
}

function formatDateLabel(dateString) {
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatCountdown(dateString, currentMs) {
  const target = new Date(dateString)
  if (Number.isNaN(target.getTime())) return { days: '—', hours: '—', minutes: '—' }
  const diff = target.getTime() - (currentMs || Date.now())
  if (diff <= 0) return { days: '0', hours: '0', minutes: '0' }
  const minutesTotal = Math.floor(diff / 60000)
  const days = Math.floor(minutesTotal / 1440)
  const hours = Math.floor((minutesTotal % 1440) / 60)
  const minutes = minutesTotal % 60
  return { days: String(days).padStart(2, '0'), hours: String(hours).padStart(2, '0'), minutes: String(minutes).padStart(2, '0') }
}

function observationDifficulty(distanceAU, magnitude) {
  if (distanceAU <= 0.12 && magnitude <= 12) return 'Excellent'
  if (distanceAU <= 0.2 && magnitude <= 14) return 'Good'
  if (distanceAU <= 0.35) return 'Moderate'
  return 'Challenging'
}

function AsteroidsTab() {
  const { homeCity, setHomeCity } = useAppShell()
  const [days, setDays] = useState(30)
  const [distanceAU, setDistanceAU] = useState('0.2')
  const [minDiameter, setMinDiameter] = useState('100')
  const [approaches, setApproaches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const loadApproaches = async () => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({ days: String(days), distanceAU, minDiameter })
        const res = await fetch(`/api/neo-approaches?${params}`)
        if (!res.ok) {
          const body = await res.text()
          throw new Error(body || `NeoWS ${res.status}`)
        }
        const data = await res.json()
        if (!cancelled) setApproaches(data.approaches || [])
      } catch (err) {
        if (!cancelled) setError(err?.message || 'Unable to load asteroid close approaches.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadApproaches()
    return () => {
      cancelled = true
    }
  }, [days, distanceAU, minDiameter])

  const bestApproaches = useMemo(() => {
    if (!approaches?.length) return []
    return approaches.slice(0, 3)
  }, [approaches])

  const recommendationCards = useMemo(() => {
    const items = []
    if (bestApproaches.length > 0) {
      items.push({
        title: bestApproaches[0].name,
        subtitle: `${formatDateLabel(bestApproaches[0].date)} · ${bestApproaches[0].distanceAU} AU · ${bestApproaches[0].diameter}m`,
        score: '89%',
        note: `Best target for ${homeCity.split(',')[0]?.trim() || 'your location'}`,
      })
    }
    items.push({
      title: 'ISS Visibility Window',
      subtitle: 'Tonight 20:42 · Clear skies expected',
      score: '92%',
      note: 'Bright, wide-field target ideal for rapid verification',
    })
    if (bestApproaches.length > 1) {
      items.push({
        title: bestApproaches[1].name,
        subtitle: `${formatDateLabel(bestApproaches[1].date)} · ${bestApproaches[1].distanceAU} AU`,
        score: '73%',
        note: observationDifficulty(Number(bestApproaches[1].distanceAU), Number(bestApproaches[1].magnitude)),
      })
    }
    return items
  }, [bestApproaches, homeCity])

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-6">
        <GlassPanel className="p-6 relative overflow-hidden border border-slate-700/50 bg-slate-950/70">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm text-cyan-300 font-semibold uppercase tracking-[0.2em]">NASA NeoWs</p>
              <h2 className="mt-2 text-2xl font-display font-bold text-white">Asteroid Close Approach Dashboard</h2>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-400 uppercase tracking-[0.2em]">Filters</p>
              <p className="text-sm text-slate-300">Next {days} days · within {distanceAU} AU</p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 mb-6">
            <label className="text-slate-300 text-xs">
              <span className="block mb-2">Time span</span>
              <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white outline-none">
                <option value={7}>7 days</option>
                <option value={14}>14 days</option>
                <option value={30}>30 days</option>
              </select>
            </label>
            <label className="text-slate-300 text-xs">
              <span className="block mb-2">Maximum distance</span>
              <select value={distanceAU} onChange={(e) => setDistanceAU(e.target.value)} className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white outline-none">
                <option value="0.1">0.1 AU</option>
                <option value="0.2">0.2 AU</option>
                <option value="0.35">0.35 AU</option>
              </select>
            </label>
            <label className="text-slate-300 text-xs">
              <span className="block mb-2">Minimum diameter</span>
              <select value={minDiameter} onChange={(e) => setMinDiameter(e.target.value)} className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white outline-none">
                <option value="50">50 m</option>
                <option value="100">100 m</option>
                <option value="200">200 m</option>
              </select>
            </label>
          </div>

          {loading ? (
            <div className="rounded-3xl border border-slate-700/40 bg-slate-900/70 p-8 text-slate-400 text-center">Loading asteroid data...</div>
          ) : error ? (
            <div className="rounded-3xl border border-rose-500/40 bg-rose-900/20 p-8 text-rose-200 text-center">{error}</div>
          ) : (
            <div className="space-y-4">
              {bestApproaches.map((approach, index) => (
                <div key={approach.id} className="rounded-3xl border border-slate-700/50 bg-slate-900/70 p-5">
                  <div className="flex items-center justify-between gap-4 mb-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-400">#{index + 1} Close Approach</p>
                      <h3 className="text-xl font-semibold text-white">{approach.name}</h3>
                    </div>
                    <span className="rounded-full bg-cyan-500/15 px-3 py-1 text-xs font-semibold uppercase text-cyan-300">{formatDateLabel(approach.date)}</span>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-slate-700/50 bg-slate-950/80 p-4">
                      <div className="text-xs text-slate-400">Distance</div>
                      <div className="mt-2 text-lg font-semibold text-white">{approach.distanceAU} AU</div>
                    </div>
                    <div className="rounded-2xl border border-slate-700/50 bg-slate-950/80 p-4">
                      <div className="text-xs text-slate-400">Magnitude</div>
                      <div className="mt-2 text-lg font-semibold text-white">{approach.magnitude}</div>
                    </div>
                    <div className="rounded-2xl border border-slate-700/50 bg-slate-950/80 p-4">
                      <div className="text-xs text-slate-400">Size</div>
                      <div className="mt-2 text-lg font-semibold text-white">{approach.diameter} m</div>
                    </div>
                    <div className="rounded-2xl border border-slate-700/50 bg-slate-950/80 p-4">
                      <div className="text-xs text-slate-400">Velocity</div>
                      <div className="mt-2 text-lg font-semibold text-white">{approach.velocity} km/s</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassPanel>

        <GlassPanel className="p-6 bg-slate-950/70 border border-slate-700/50 rounded-3xl">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-xl font-semibold text-white">Asteroid Observation Planner</h3>
              <p className="text-sm text-slate-400">Refine your observing strategy for the next close approach window.</p>
            </div>
            <span className="text-xs uppercase tracking-[0.2em] text-slate-500">{homeCity.split(',')[0] || 'Location'}</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 mb-5">
            <div className="rounded-2xl border border-slate-700/50 bg-slate-900/80 p-4">
              <span className="text-xs text-slate-400">Equipment</span>
              <p className="mt-2 text-white font-semibold">Small Telescope</p>
            </div>
            <div className="rounded-2xl border border-slate-700/50 bg-slate-900/80 p-4">
              <span className="text-xs text-slate-400">Best window</span>
              <p className="mt-2 text-white font-semibold">Next 48 hours</p>
            </div>
          </div>
          <div className="space-y-4">
            {recommendationCards.map((card) => (
              <div key={card.title} className="rounded-3xl border border-slate-700/50 bg-slate-900/80 p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs uppercase tracking-[0.2em] text-slate-400">{card.score}</span>
                  <span className="text-xs text-slate-500">{card.note}</span>
                </div>
                <h4 className="text-base font-semibold text-white">{card.title}</h4>
                <p className="text-sm text-slate-400 mt-1">{card.subtitle}</p>
              </div>
            ))}
          </div>
        </GlassPanel>
      </div>

      <GlassPanel className="p-6 bg-slate-950/70 border border-slate-700/50 rounded-3xl">
        <div className="mb-5">
          <h3 className="text-xl font-semibold text-white">AI Observatory Insights</h3>
          <p className="text-sm text-slate-400">Combine NASA NeoWs hazard data with launch and visibility intelligence.</p>
        </div>
        <div className="grid gap-4">
          <div className="rounded-3xl border border-slate-700/50 bg-slate-900/80 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs uppercase tracking-[0.2em] text-slate-400">Prediction</span>
              <span className="text-xs text-emerald-400">Optimal</span>
            </div>
            <p className="text-lg font-semibold text-white">{bestApproaches[0]?.name ?? 'No target yet'}</p>
            <p className="text-sm text-slate-400 mt-2">Target looks best under dark skies with a small telescope.</p>
          </div>
          <div className="rounded-3xl border border-slate-700/50 bg-slate-900/80 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs uppercase tracking-[0.2em] text-slate-400">Visibility</span>
              <span className="text-xs text-cyan-300">{bestApproaches[0] ? observationDifficulty(Number(bestApproaches[0].distanceAU), Number(bestApproaches[0].magnitude)) : 'TBD'}</span>
            </div>
            <p className="text-sm text-slate-400">{bestApproaches[0] ? `${bestApproaches[0].name} is the strongest candidate in your selected window.` : 'Change filters to load close approaches.'}</p>
          </div>
          <div className="rounded-3xl border border-slate-700/50 bg-slate-900/80 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs uppercase tracking-[0.2em] text-slate-400">Recommendation</span>
              <span className="text-xs text-amber-300">Binoculars+</span>
            </div>
            <p className="text-sm text-slate-400">Focus on targets with bright magnitudes and low orbital distance for the best chance of capture.</p>
          </div>
        </div>
      </GlassPanel>
    </motion.div>
  )
}

function LaunchesTab() {
  const [agencyFilters, setAgencyFilters] = useState(['All Agencies'])
  const [days, setDays] = useState(90)
  const [launches, setLaunches] = useState([])
  const [launchLoading, setLaunchLoading] = useState(true)
  const [launchError, setLaunchError] = useState(null)
  const [mounted, setMounted] = useState(false)

  const agencyOptions = ['All Agencies', 'ISRO', 'SpaceX', 'NASA', 'Others']
  const [launchProb, setLaunchProb] = useState(null)

  useEffect(() => {
    setMounted(true)
    fetch('http://localhost:8000/api/launch/probability')
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setLaunchProb(d) })
      .catch(() => {})
  }, [])

  const selectedAgencies = useMemo(() => {
    if (agencyFilters.includes('All Agencies')) return ['All Agencies']
    return agencyFilters.length ? agencyFilters : ['All Agencies']
  }, [agencyFilters])

  useEffect(() => {
    let cancelled = false
    const loadLaunches = async () => {
      setLaunchLoading(true)
      setLaunchError(null)
      try {
        const params = new URLSearchParams({ days: String(days), agencies: selectedAgencies.join(',') })
        const res = await fetch(`/api/launches?${params}`)
        if (!res.ok) {
          const body = await res.text()
          throw new Error(body || `Launch API ${res.status}`)
        }
        const data = await res.json()
        if (!cancelled) setLaunches(data.launches || [])
      } catch (err) {
        if (!cancelled) setLaunchError(err?.message || 'Unable to retrieve launch schedule.')
      } finally {
        if (!cancelled) setLaunchLoading(false)
      }
    }
    loadLaunches()
    return () => {
      cancelled = true
    }
  }, [days, selectedAgencies])

  const providerLabel = (name) => name || 'Unknown'

  const nextIsroLaunch = useMemo(() => {
    const found = launches.find((launch) =>
      (launch.launch_service_provider?.name || '').toLowerCase().includes('isro')
    )
    if (found) return found
    return {
      id: 'fallback-isro',
      name: 'PSLV-C59 / PROBA-3',
      launch_service_provider: { name: 'ISRO' },
      pad: { name: 'Satish Dhawan Space Centre' },
      window_start: '2025-02-15T14:30:00Z',
      status: { name: 'TBD' },
      mission: { name: 'ESA Solar Mission' },
    }
  }, [launches])

  const countdown = formatCountdown(nextIsroLaunch.window_start, mounted ? Date.now() : new Date('2025-02-01T00:00:00Z').getTime())

  const displayLaunches = useMemo(() => {
    if (launches.length > 0) return launches.slice(0, 5)
    return [
      {
        id: 'fallback-1',
        name: 'Starlink Group 7-14',
        launch_service_provider: { name: 'SpaceX' },
        window_start: '2025-02-01T14:00:00Z',
        pad: { name: 'Cape Canaveral SLC-40' },
        status: { name: 'Go' },
        mission: { name: 'Communications array' },
      },
      {
        id: 'fallback-2',
        name: 'NGLV Test Flight',
        launch_service_provider: { name: 'ISRO' },
        window_start: '2025-02-10T09:30:00Z',
        pad: { name: 'Sriharikota' },
        status: { name: 'Pending' },
        mission: { name: 'Heavy-lift demonstrator' },
      },
      {
        id: 'fallback-3',
        name: 'Artemis III (Tentative)',
        launch_service_provider: { name: 'NASA' },
        window_start: '2025-03-05T18:00:00Z',
        pad: { name: 'Kennedy LC-39B' },
        status: { name: 'Tentative' },
        mission: { name: 'Lunar crew rotation' },
      },
    ]
  }, [launches])

  const agencyCheckboxes = agencyOptions.map((option) => {
    const checked = selectedAgencies.includes(option)
    return (
      <label className="flex items-center gap-2 text-sm text-slate-300" key={option}>
        <input
          type="checkbox"
          checked={checked}
          onChange={() => {
            setAgencyFilters((current) => {
              if (option === 'All Agencies') return ['All Agencies']
              const next = current.includes(option)
                ? current.filter((item) => item !== option)
                : [...current.filter((item) => item !== 'All Agencies'), option]
              return next.length ? next : ['All Agencies']
            })
          }}
          className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-cyan-400 focus:ring-cyan-500"
        />
        <span>{option}</span>
      </label>
    )
  })

  const scheduleTitle = launchLoading ? 'Fetching launch schedule…' : launchError ? 'Launch schedule unavailable' : `Showing ${agencyFilters.join(', ')}`

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-6">
        <GlassPanel className="p-8 relative overflow-hidden bg-gradient-to-b from-[#111827]/80 to-[#1e1b4b]/40">
          <div className="inline-block px-3 py-1 rounded-full text-xs font-bold bg-orange-900/40 text-orange-400 border border-orange-500/30 uppercase tracking-wider mb-6">
            🇮🇳 Next ISRO Launch
          </div>

          <h2 className="text-3xl font-display font-bold text-white mb-2">{nextIsroLaunch.name}</h2>
          <p className="text-slate-400 mb-2">{nextIsroLaunch.mission?.name || 'Mission details pending'}</p>
          <p className="text-slate-500 text-sm">Launch pad: {nextIsroLaunch.pad?.name || 'TBD'}</p>

          <div className="grid grid-cols-4 gap-4 my-8">
            <div className="bg-[#0e121e]/80 p-4 rounded-2xl border border-slate-700/50 text-center">
              <div className="text-3xl font-bold text-orange-400 mb-1">{countdown.days}</div>
              <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Days</div>
            </div>
            <div className="bg-[#0e121e]/80 p-4 rounded-2xl border border-slate-700/50 text-center">
              <div className="text-3xl font-bold text-white mb-1">{countdown.hours}</div>
              <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Hours</div>
            </div>
            <div className="bg-[#0e121e]/80 p-4 rounded-2xl border border-slate-700/50 text-center">
              <div className="text-3xl font-bold text-white mb-1">{countdown.minutes}</div>
              <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Mins</div>
            </div>
            <div className="bg-[#0e121e]/80 p-4 rounded-2xl border border-slate-700/50 text-center">
              <div className="text-3xl font-bold text-white mb-1">00</div>
              <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Secs</div>
            </div>
          </div>

          <div className="bg-indigo-900/30 border border-indigo-500/30 rounded-xl p-5 mb-6">
            <div className="flex justify-between items-center mb-4">
              <div className="text-indigo-400 font-bold flex items-center gap-2">
                🤖 AI PREDICTION (On-Time)
              </div>
              <div className={`text-2xl font-bold ${
                launchProb
                  ? launchProb.probability_pct >= 65
                    ? 'text-emerald-400'
                    : launchProb.probability_pct >= 35
                    ? 'text-amber-400'
                    : 'text-rose-400'
                  : 'text-white'
              }`}>
                {launchProb ? `${launchProb.probability_pct}%` : '78%'}
              </div>
            </div>

            <div className="space-y-3 text-sm text-slate-300">
              {launchProb ? (
                <>
                  <div className="flex justify-between">
                    <span>Risk Level</span>
                    <span className={
                      launchProb.risk_level === 'Favorable' ? 'text-emerald-400' :
                      launchProb.risk_level === 'Moderate'  ? 'text-amber-400'   :
                      'text-rose-400'
                    }>
                      {launchProb.risk_level}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Temperature</span>
                    <span className="text-slate-300">
                      {launchProb.based_on_weather?.temperature_c?.toFixed(1)}°C
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Humidity</span>
                    <span className={
                      launchProb.based_on_weather?.humidity_pct > 80
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                    }>
                      {launchProb.based_on_weather?.humidity_pct?.toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Wind Speed</span>
                    <span className={
                      launchProb.based_on_weather?.wind_speed_ms > 10
                        ? 'text-rose-400'
                        : 'text-emerald-400'
                    }>
                      {launchProb.based_on_weather?.wind_speed_ms?.toFixed(1)} m/s
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Monsoon Season</span>
                    <span className={
                      launchProb.based_on_weather?.is_monsoon_season
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                    }>
                      {launchProb.based_on_weather?.is_monsoon_season ? 'Yes ⚠️' : 'No ✓'}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 pt-2 border-t border-indigo-500/20">
                    Model: {launchProb.model_version} · Threshold: {launchProb.threshold}
                  </div>
                </>
              ) : (
                <>
                  <div className="flex justify-between">
                    <span>Weather Risk</span>
                    <span className="text-amber-400">15% (Monsoon ending)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Technical Risk</span>
                    <span className="text-emerald-400">7% (PSLV highly reliable)</span>
                  </div>
                  <div className="text-xs text-slate-500 pt-2 border-t border-indigo-500/20">
                    Similar past launches: 28/32 on-time (87.5%)
                  </div>
                </>
              )}
            </div>

            <div className="mt-4 flex gap-3">
              <button className="flex-1 bg-slate-800 hover:bg-slate-700 text-xs font-semibold py-2 rounded-lg transition-colors border border-slate-600">
                ✅ Verify Prediction
              </button>
            </div>
          </div>

          <div className="flex gap-4 flex-col md:flex-row">
            <button className="flex-1 bg-orange-500 hover:bg-orange-600 text-white font-semibold py-3 rounded-xl transition-colors shadow-[0_0_15px_rgba(249,115,22,0.4)]">🔔 Alert Me</button>
            <button className="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3 rounded-xl transition-colors border border-slate-700">📺 Watch Live</button>
          </div>
        </GlassPanel>
      </div>

      <div className="space-y-6">
        <GlassPanel className="p-0 overflow-hidden">
          <div className="bg-slate-800/80 p-5 border-b border-slate-700/50">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="font-display font-semibold text-white tracking-wide">🚀 Global Launch Schedule</h3>
                <p className="text-slate-400 text-sm">{scheduleTitle}</p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <div className="text-xs text-slate-400 uppercase tracking-wider">Window</div>
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="bg-slate-900 border border-slate-700 text-xs text-slate-300 rounded px-2 py-1 outline-none"
                >
                  <option value={30}>30 days</option>
                  <option value={60}>60 days</option>
                  <option value={90}>90 days</option>
                </select>
              </div>
            </div>
          </div>

          <div className="p-5 space-y-3 border-b border-slate-700/50">
            <div className="grid grid-cols-2 gap-3">{agencyCheckboxes}</div>
          </div>

          <div className="divide-y divide-slate-800/50">
            {launchLoading ? (
              <div className="p-5 text-sm text-slate-400">Fetching launch schedule…</div>
            ) : launchError ? (
              <div className="p-5 text-sm text-amber-300">{launchError}</div>
            ) : (
              displayLaunches.map((launch) => {
                const date = new Date(launch.window_start)
                const day = date.toLocaleDateString('en-US', { day: '2-digit' })
                const month = date.toLocaleDateString('en-US', { month: 'short' })
                const provider = providerLabel(launch.launch_service_provider?.name)
                const status = launch.status?.name || 'Pending'
                const onTime = provider.toLowerCase().includes('spacex')
                  ? '95%'
                  : provider.toLowerCase().includes('isro')
                  ? (launchProb ? `${launchProb.probability_pct}%` : '78%')
                  : provider.toLowerCase().includes('nasa')
                  ? '84%'
                  : '72%'

                return (
                  <div key={launch.id || launch.name} className="p-5 hover:bg-slate-800/30 transition-colors">
                    <div className="flex gap-4 items-center">
                      <div className="text-center min-w-[60px]">
                        <div className="text-sm font-bold text-slate-400 uppercase">{month}</div>
                        <div className="text-2xl font-display font-bold text-white">{day}</div>
                      </div>
                      <div className="flex-1">
                        <div className="text-xs text-slate-400 font-bold tracking-widest uppercase mb-1">{provider}</div>
                        <div className="text-lg font-bold text-white mb-2">{launch.name}</div>
                        <div className="text-xs text-slate-400 mb-2">{launch.pad?.name ?? 'Launch pad TBD'}</div>
                        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-bold bg-slate-900/80 text-slate-200 border border-slate-700/50">
                          {status} · {onTime} Prob
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </GlassPanel>
      </div>
    </motion.div>
  )
}

// --------------------------------------------------------------------------------
// MAIN COMPONENT
// --------------------------------------------------------------------------------

export default function AstronomyHub() {
  const tabs = [
    { value: 'satellites', label: '🌍 Satellites' },
    { value: 'asteroids', label: '🌠 Asteroids' },
    { value: 'launches', label: '🚀 Launches' },
    { value: 'sun', label: '☀️ Sun' }
  ]
  const [activeTab, setActiveTab] = useState('satellites')

  return (
    <div className="min-h-screen bg-[#0a0e17] text-slate-200 font-body">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-8 py-8">
        
        {/* Header Area */}
        <div className="mb-8">
          <h1 className="text-3xl font-display font-bold text-white tracking-wide mb-2">Astronomy Hub</h1>
          <p className="text-slate-400">Track orbital objects, predict visibility, and monitor global space launches.</p>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-8 border-b border-slate-800 mb-8 overflow-x-auto custom-scrollbar pb-1">
          {tabs.map(t => {
            const isActive = activeTab === t.value
            return (
              <button
                key={t.value}
                onClick={() => setActiveTab(t.value)}
                className={cn(
                  "relative pb-4 text-base font-medium tracking-wide transition-colors whitespace-nowrap",
                  isActive ? "text-cyan-400" : "text-slate-400 hover:text-slate-200"
                )}
              >
                {t.label}
                {isActive && (
                  <motion.div
                    layoutId="astronomyTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.8)]"
                  />
                )}
              </button>
            )
          })}
        </div>

        {/* Tab Content Area */}
        <AnimatePresence mode="wait">
          {activeTab === 'satellites' && <SatellitesTab key="satellites" />}
          {activeTab === 'asteroids' && <AsteroidsTab key="asteroids" />}
          {activeTab === 'launches' && <LaunchesTab key="launches" />}
          {activeTab === 'sun' && (
            <motion.div key="sun" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="flex items-center justify-center h-[500px]">
              <div className="text-center">
                <div className="text-6xl mb-4">☀️</div>
                <h3 className="text-xl font-display font-bold text-slate-300">Sun Monitoring (Coming Soon)</h3>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  )
}
