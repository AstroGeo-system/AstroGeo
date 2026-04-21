'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAppShell } from '@/components/providers/AppShellProvider'
import { api } from '@/lib/api'
import dynamic from 'next/dynamic'

const MapComponent = dynamic(() => import('./LeafletMap'), { 
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-slate-900/50">
      <div className="text-slate-400 font-medium">Loading Interactive Map...</div>
    </div>
  ) 
})

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

function extractLngLatPairs(coords, acc = []) {
  if (!Array.isArray(coords)) return acc
  if (
    coords.length >= 2 &&
    typeof coords[0] === 'number' &&
    typeof coords[1] === 'number'
  ) {
    acc.push([coords[0], coords[1]])
    return acc
  }
  coords.forEach((child) => extractLngLatPairs(child, acc))
  return acc
}

function isWithinIndiaBounds(lng, lat) {
  return lng >= 68 && lng <= 98 && lat >= 6 && lat <= 38
}

function isIndiaEONETEvent(event) {
  const points = (event?.geometry ?? []).flatMap((geom) => extractLngLatPairs(geom?.coordinates))
  return points.some(([lng, lat]) => isWithinIndiaBounds(lng, lat))
}

function GlassPanel({ children, className }) {
  return (
    <div className={cn("bg-[#111827]/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden", className)}>
      {children}
    </div>
  )
}

function getMapUrl(tab) {
  const base = "https://maps-492903.projects.earthengine.app/view/map"
  if (tab === "vegetation") return `${base}?mode=NDVI`
  if (tab === "drought")    return `${base}?mode=Drought`
  if (tab === "floods")     return `${base}?mode=Flood`
  if (tab === "urban")      return `${base}?mode=Urban`
  return base
}

const DEFAULT_ZONES = [
  'Andhra Pradesh', 'Bihar', 'Gujarat', 'Himachal Pradesh', 'Karnataka',
  'Madhya Pradesh', 'Maharashtra', 'Odisha', 'Punjab', 'Rajasthan',
  'Tamil Nadu', 'Telangana', 'Uttar Pradesh', 'West Bengal',
]

function unique(values) {
  return Array.from(new Set(values.filter(Boolean)))
}

// ── Vegetation Tab ───────────────────────────────────────────────
function VegetationTab({ geoData }) {
  const { homeCity } = useAppShell()
  const [zone,     setZone]     = useState('Maharashtra')
  const [zones,    setZones]    = useState(DEFAULT_ZONES)
  const [zoneToStates, setZoneToStates] = useState({})
  const [year,     setYear]     = useState('2026 Live')
  const [ndviData, setNdviData] = useState(null)
  const [change,   setChange]   = useState(null)
  const [allMetrics, setAllMetrics] = useState({})
  const [loading,  setLoading]  = useState(false)

  const YEARS = ['2026 Live', '2025', '2024', '2023', '2022', '2021']

  useEffect(() => {
    let cancelled = false
    api.getEarthZones().then((res) => {
      if (cancelled || !res) return
      const fromStates = Array.isArray(res.states) ? res.states : []
      const merged = unique([...fromStates, ...DEFAULT_ZONES]).sort((a, b) => a.localeCompare(b))
      if (merged.length > 0) setZones(merged)
      if (res.zone_to_states && typeof res.zone_to_states === 'object') {
        setZoneToStates(res.zone_to_states)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    const activeYear = year === '2026 Live' ? 2026 : parseInt(year, 10)
    const ndviPromise = year === '2026 Live' 
          ? api.getLiveNDVI(zone, activeYear) 
          : api.getNDVI(zone, activeYear)

    const allNdviPromises = zones.map(z =>
          year === '2026 Live' ? api.getLiveNDVI(z, activeYear) : api.getNDVI(z, activeYear)
    )

    Promise.all([
      ndviPromise,
      api.getChange(zone),
      Promise.all(allNdviPromises)
    ]).then(([ndvi, changeData, allNdviRes]) => {
      setNdviData(ndvi)
      setChange(changeData)
      
      const metricsObj = {}
      allNdviRes.forEach((res, idx) => {
         if (res?.summary?.mean_ndvi != null) {
            const selectedZone = zones[idx]
            metricsObj[selectedZone] = res.summary.mean_ndvi
            const sourceZone = String(res?.zone || '').toLowerCase()
            const expandedStates = zoneToStates[sourceZone]
            if (Array.isArray(expandedStates)) {
              expandedStates.forEach((state) => {
                metricsObj[state] = res.summary.mean_ndvi
              })
            }
         }
      })
      setAllMetrics(metricsObj)
      
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [zone, year, zones, zoneToStates])

  // Pull the most significant change from the timeline
  const latestChanges = (() => {
    if (!change?.timeline) return []
    const years  = Object.keys(change.timeline).sort()
    const latest = change.timeline[years[years.length - 1]] ?? []
    return latest.slice(0, 3)
  })()

  const summary = ndviData?.summary ?? {}

  return (
    <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-160px)] min-h-[600px]">
      
      {/* Interactive Map Area */}
      <div className="lg:col-span-8 h-full">
        <GlassPanel className="h-full w-full p-6 flex flex-col relative">
          <p className="text-[11px] text-slate-500 mb-2 z-10">
            Observation & weather baseline: <span className="text-slate-400">{homeCity}</span>
          </p>
          <div className="flex justify-between items-center mb-6 z-10">
            <h2 className="font-display font-semibold text-lg text-white flex items-center gap-2">🌱 NDVI (Vegetation Health) MONITORING</h2>
            <div className="flex gap-2">
              <select
                value={zone}
                onChange={e => setZone(e.target.value)}
                className="bg-slate-900/80 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-1.5 outline-none focus:border-cyan-500"
              >
                {zones.map(z => <option key={z}>{z}</option>)}
              </select>
              <select
                value={year}
                onChange={e => setYear(e.target.value)}
                className="bg-slate-900/80 border border-emerald-500/50 text-emerald-400 font-bold text-sm rounded-lg px-3 py-1.5 outline-none focus:border-emerald-400"
              >
                {YEARS.map(y => <option key={y}>{y}</option>)}
              </select>
            </div>
          </div>

          <div className="flex-1 bg-[#0a0e17]/80 rounded-xl border border-slate-700/50 relative overflow-hidden flex flex-col items-center justify-center">
             <MapComponent 
                 className="w-full h-full absolute inset-0 rounded-xl"
                 zone={zone}
                 allMetrics={allMetrics}
                 metricValue={ndviData?.summary?.mean_ndvi}
                 mode="vegetation"
                 geoJsonData={geoData}
             />
             <div className="absolute top-4 right-4 bg-slate-900/80 backdrop-blur-md p-3 rounded-lg border border-slate-700/50 text-xs text-slate-300 space-y-1.5 z-10">
               <div className="font-semibold text-white mb-2 pb-1 border-b border-slate-700">Legend</div>
               <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-green-500" /> Healthy (NDVI {'>'} 0.6)</div>
               <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-yellow-500" /> Moderate (0.3-0.6)</div>
               <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-red-500" /> Poor (NDVI {'<'} 0.3)</div>
             </div>
          </div>

          {/* Time Slider */}
          <div className="mt-6 z-10 bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
            <div className="flex justify-between text-xs text-slate-400 font-bold tracking-wider mb-2">
              <span>2018</span>
              <span>2022</span>
              <span className="text-white">2026</span>
            </div>
            <div className="relative h-2 bg-slate-700 rounded-full">
               <div className="absolute top-0 left-0 h-full w-[95%] bg-green-500 rounded-full shadow-[0_0_10px_rgba(34,197,94,0.5)]" />
               <div className="absolute top-1/2 left-[95%] -translate-x-1/2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-green-500 rounded-full cursor-pointer shadow-lg" />
            </div>
          </div>
        </GlassPanel>
      </div>

      {/* Change Detection Panel */}
      <div className="lg:col-span-4 h-full">
        <GlassPanel className="h-full p-6 flex flex-col border-t-4 border-t-red-500 bg-gradient-to-b from-red-900/10 to-transparent">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <h3 className="font-display font-bold text-lg text-white">AI-DETECTED CHANGES</h3>
            <span className="ml-auto text-xs text-slate-500">2018 → 2024</span>
          </div>

          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="w-8 h-8 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
            </div>
          ) : (
            <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-5 mb-6 flex-1">
              {/* NDVI summary */}
              {summary.mean_ndvi != null ? (
                <>
                  <div className="text-red-400 font-bold mb-1">
                    {summary.dominant_class === 'vegetation_loss'
                      ? '🚨 Significant NDVI Drop Detected'
                      : summary.dominant_class === 'stable_vegetation'
                      ? '✅ Vegetation Stable'
                      : '⚠️ Land Cover Change Detected'}
                  </div>
                  <div className="text-sm text-slate-300 mb-4">
                    📍 {zone}<br/>
                    📅 NDVI Mean: <span className="text-cyan-400 font-bold">{summary.mean_ndvi.toFixed(3)}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-5">
                    <div className="bg-slate-900/60 p-2 rounded border border-slate-700">
                      <span className="text-xs text-slate-400 block">Total Δ NDVI</span>
                      <span className={summary.delta_total < 0 ? 'text-red-400 font-bold' : 'text-emerald-400 font-bold'}>
                        {summary.delta_total != null
                          ? `${summary.delta_total > 0 ? '+' : ''}${(summary.delta_total * 100).toFixed(1)}%`
                          : '—'}
                      </span>
                    </div>
                    <div className="bg-slate-900/60 p-2 rounded border border-slate-700">
                      <span className="text-xs text-slate-400 block">Zones Analysed</span>
                      <span className="text-white font-bold">{ndviData?.results?.length ?? '—'}</span>
                    </div>
                  </div>

                  {/* Zone breakdown */}
                  {latestChanges.length > 0 && (
                    <div className="border border-indigo-500/30 bg-indigo-900/20 rounded-lg p-4">
                      <div className="text-sm font-bold text-indigo-400 mb-2 flex items-center gap-2">🤖 ZONE BREAKDOWN</div>
                      <div className="space-y-2">
                        {latestChanges.map((z, i) => (
                          <div key={i} className="flex flex-col gap-1 text-xs px-3 py-2 bg-slate-800/60 rounded border border-slate-700/50">
                            <span className="text-white font-bold">{z.zone_name}</span>
                            <span className={z.change_class === 'vegetation_loss' ? 'text-red-400 font-bold' : 'text-emerald-400'}>
                              {z.change_class?.replace(/_/g, ' ')}
                              {z.confidence != null ? ` (${(z.confidence * 100).toFixed(0)}%)` : ''}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                // Fallback static display (if backend is down)
                <div className="flex items-center justify-center h-full">
                  <div className="text-center p-6 border border-slate-700/50 rounded-xl bg-slate-900/60 w-full">
                     <div className="text-4xl mb-4">📡</div>
                     <h3 className="text-lg font-bold text-slate-300 mb-2">Awaiting Live Connection</h3>
                     <p className="text-sm text-slate-400 mb-4">
                       Ensure your AI backend is running and the frontend is configured with{' '}
                       <code className="bg-black/30 px-2 py-1 rounded">NEXT_PUBLIC_API_URL</code> to view the {year} data stream.
                     </p>
                     <p className="text-xs text-slate-500">The map will automatically populate once connected.</p>
                  </div>
                </div>
              )}

              <div className="flex gap-2 mt-5">
                <button className="flex-1 bg-slate-800 hover:bg-slate-700 text-xs text-white font-semibold py-2 rounded transition-colors border border-slate-600">✅ Verify</button>
                <button className="flex-1 bg-slate-800 hover:bg-slate-700 text-xs text-white font-semibold py-2 rounded transition-colors border border-slate-600">📄 Report</button>
              </div>
            </div>
          )}
        </GlassPanel>
      </div>

    </motion.div>
  )
}

// ── Drought Tab ──────────────────────────────────────────────────
function DroughtTab({ geoData }) {
  const { homeCity } = useAppShell()
  const [district,     setDistrict]     = useState('Maharashtra')
  const [districts,    setDistricts]    = useState(DEFAULT_ZONES)
  const [year,         setYear]         = useState('2026')
  const [droughtData,  setDroughtData]  = useState(null)
  const [allDrought,   setAllDrought]   = useState({})
  const [loading,      setLoading]      = useState(false)

  const YEARS = ['2026', '2025', '2024', '2023', '2022', '2021']

  useEffect(() => {
    let cancelled = false
    api.getEarthZones().then((res) => {
      if (cancelled || !res) return
      const fromStates = Array.isArray(res.states) ? res.states : []
      const merged = unique([...fromStates, ...DEFAULT_ZONES]).sort((a, b) => a.localeCompare(b))
      if (merged.length > 0) setDistricts(merged)
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    const yearParam = year ? `?year=${year}` : ''

    // Fetch selected district + all districts for map coverage in parallel
    const selectedPromise = fetch(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/agro/drought/${encodeURIComponent(district)}${yearParam}`,
      { cache: 'no-store' }
    ).then(r => r.ok ? r.json() : null).catch(() => null)

    const allPromises = districts.map(d =>
      fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/agro/drought/${encodeURIComponent(d)}${yearParam}`,
        { cache: 'no-store' }
      ).then(r => r.ok ? r.json() : null).catch(() => null)
    )

    Promise.all([selectedPromise, Promise.all(allPromises)]).then(([selected, all]) => {
      setDroughtData(selected)
      const metricsObj = {}
      all.forEach((res, idx) => {
        if (res?.drought_score != null) {
          metricsObj[districts[idx]] = res.drought_score
        }
      })
      setAllDrought(metricsObj)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [district, year, districts])

  const severityColor = {
    Severe:   'border-red-500 text-red-500',
    Moderate: 'border-orange-500 text-orange-400',
    Mild:     'border-yellow-500 text-yellow-400',
    None:     'border-emerald-500 text-emerald-400',
  }[droughtData?.severity] ?? 'border-red-500 text-red-500'

  return (
    <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-6">
        <GlassPanel className="p-6">
          <p className="text-[11px] text-slate-500 mb-4">
            Weather & analysis baseline: <span className="text-slate-400">{homeCity}</span>
          </p>
          <div className="flex justify-between items-center mb-6">
            <h2 className="font-display font-semibold text-lg text-white flex items-center gap-2">💧 AGRICULTURAL DROUGHT MONITOR</h2>
            <div className="flex gap-2">
              <select
                value={district}
                onChange={e => setDistrict(e.target.value)}
                className="bg-slate-900/80 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1.5 outline-none"
              >
                {districts.map(d => <option key={d}>{d}</option>)}
              </select>
              <select
                value={year}
                onChange={e => setYear(e.target.value)}
                className="bg-slate-900/80 border border-emerald-500/50 text-emerald-400 font-bold text-xs rounded-lg px-2 py-1.5 outline-none"
              >
                {YEARS.map(y => <option key={y}>{y}</option>)}
              </select>
            </div>
          </div>

          <div className="w-full h-[400px] bg-[#0a0e17]/80 rounded-xl border border-slate-700/50 flex flex-col items-center justify-center relative shadow-inner overflow-hidden">
             <MapComponent 
                 className="w-full h-full absolute inset-0 rounded-xl"
                 zone={district}
                 metricValue={droughtData?.drought_score}
                 allMetrics={allDrought}
                 mode="drought"
                 geoJsonData={geoData}
             />
            
            <div className="absolute bottom-4 left-4 bg-slate-900/90 backdrop-blur-md p-3 rounded-lg border border-slate-700/70 text-xs">
              <div className="font-semibold text-white mb-2 border-b border-slate-700 pb-1">Severity Scale</div>
              <div className="space-y-1.5 text-slate-300">
                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-yellow-400" /> D0 Abnormally Dry</div>
                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-orange-400" /> D1 Moderate</div>
                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-red-500" /> D2 Severe</div>
                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-slate-800" /> D3 Extreme</div>
                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-purple-600" /> D4 Exceptional</div>
              </div>
            </div>
          </div>
        </GlassPanel>
      </div>

      <div className="space-y-6">
        <GlassPanel className="p-6 border-l-4 border-l-red-500 bg-gradient-to-bl from-[#111827]/80 to-red-900/10">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-10 h-10 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
            </div>
          ) : droughtData ? (
            <>
              <div className="flex justify-between items-start mb-6">
                <div>
                  <div className="text-xs font-bold text-slate-400 tracking-widest uppercase mb-1">District Analysis</div>
                  <h2 className="font-display font-bold text-xl text-white">{droughtData.district ?? district}</h2>
                </div>
                <div className="text-right">
                  <div className={`inline-block px-3 py-1 bg-red-500/20 border ${severityColor} border-dashed rounded font-bold text-sm mb-1`}>
                    {droughtData.severity} Drought 🔴
                  </div>
                  <div className="text-xs text-slate-500">Score: {droughtData.drought_score}</div>
                </div>
              </div>

              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-5 mb-5 space-y-4">
                <div className="flex items-center gap-2 mb-2 text-indigo-400 font-bold text-sm">🤖 DROUGHT COMPONENTS</div>
                <div className="grid grid-cols-2 gap-4">
                  {droughtData.components && Object.entries(droughtData.components).map(([key, val]) => (
                    <div key={key}>
                      <div className="text-xs text-slate-400 mb-1 capitalize">{key.replace(/_/g, ' ')}</div>
                      <div className={`text-xl font-bold ${val < 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                        {typeof val === 'number' ? val.toFixed(2) : val}
                      </div>
                    </div>
                  ))}
                </div>
                {droughtData.recommendation && (
                  <div className="text-xs font-medium text-amber-500 bg-amber-500/10 p-2 rounded">
                    ⚠️ {droughtData.recommendation}
                  </div>
                )}
              </div>

              <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-5">
                <h4 className="text-sm font-bold text-white mb-4 border-b border-slate-700 pb-2">🌾 CROP YIELD IMPACT PREDICTION</h4>
                <div className="space-y-3">
                  <div className="flex justify-between items-end">
                    <span className="text-sm text-slate-300">Estimated Yield Impact</span>
                    <span className={`text-lg font-bold ${droughtData.drought_score > 0.6 ? 'text-red-400' : 'text-amber-400'}`}>
                      {droughtData.drought_score > 0.6 ? '-25% loss' : '-10% risk'}
                    </span>
                  </div>
                  <div className="flex justify-between items-end">
                    <span className="text-sm text-slate-400">Drought Intensity</span>
                    <span className="text-sm font-medium text-slate-300">{(droughtData.drought_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <div className="mt-6 flex gap-2">
                  <button className="flex-1 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-400 text-xs font-bold py-2 rounded-lg transition-colors border border-indigo-500/50">✅ Verify Prediction</button>
                  <button className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold py-2 rounded-lg transition-colors border border-slate-600">📥 Download Report</button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center p-6 border border-slate-700/50 rounded-xl bg-slate-900/60 w-full">
                 <div className="text-4xl mb-4">📡</div>
                 <h3 className="text-lg font-bold text-slate-300 mb-2">Drought feed unavailable</h3>
                 <p className="text-sm text-slate-400 mb-4">No live drought record was returned from the backend for this district.</p>
                 <p className="text-xs text-slate-500">This view no longer shows fabricated fallback values.</p>
              </div>
            </div>
          )}
        </GlassPanel>
      </div>
    </motion.div>
  )
}

function EONETLiveTab({ categoryHint, title }) {
  const [eventsData, setEventsData] = useState(null)
  const [allEventsData, setAllEventsData] = useState(null)
  const [categoriesData, setCategoriesData] = useState(null)
  const [layersData, setLayersData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      const query = new URLSearchParams({ limit: '20', status: 'all', days: '120' })
      if (categoryHint) query.set('category', categoryHint)
      const allEventsQuery = new URLSearchParams({ limit: '40', status: 'all', days: '120' })

      const [eventsRes, allEventsRes, categoriesRes, layersRes] = await Promise.all([
        api.getEONETEvents(query.toString()),
        api.getEONETEvents(allEventsQuery.toString()),
        api.getEONETCategories(),
        api.getEONETLayers(),
      ])
      setEventsData(eventsRes)
      setAllEventsData(allEventsRes)
      setCategoriesData(categoriesRes)
      setLayersData(layersRes)
      setLoading(false)
    }

    load().catch(() => setLoading(false))
  }, [categoryHint])

  const rawEvents = eventsData?.events ?? []
  const events = rawEvents.filter(isIndiaEONETEvent)
  const indiaAllEvents = (allEventsData?.events ?? []).filter(isIndiaEONETEvent)
  const urbanFallbackEvents = indiaAllEvents
    .filter((event) => event.categories?.every((cat) => cat.id !== 'floods'))
    .slice(0, 5)
  const categories = categoriesData?.categories ?? []
  const layersByCategory = layersData?.categories ?? []
  const selectedCategory = categories.find(c => c.id === categoryHint)
  const selectedLayers = (layersByCategory.find(c => c.id === categoryHint)?.layers ?? []).slice(0, 8)
  const activeCount = events.filter(event => event.closed == null).length
  const closedCount = Math.max(events.length - activeCount, 0)
  const showUrbanFallback = categoryHint === 'manmade' && events.length === 0 && urbanFallbackEvents.length > 0

  const formatEventTime = (rawDate) => {
    if (!rawDate) return 'Unknown time'
    const date = new Date(rawDate)
    if (Number.isNaN(date.getTime())) return 'Unknown time'
    return date.toLocaleString()
  }

  const getEventFreshness = (rawDate) => {
    if (!rawDate) return 'Historic'
    const now = Date.now()
    const ts = new Date(rawDate).getTime()
    if (Number.isNaN(ts)) return 'Historic'
    const hours = Math.floor((now - ts) / (1000 * 60 * 60))
    if (hours < 24) return 'Breaking'
    if (hours < 72) return 'Active'
    return 'Historic'
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-8">
        <GlassPanel className="p-6">
          <div className="mb-5">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
              <h2 className="font-display font-semibold text-lg text-white">{title} (Live NASA EONET)</h2>
              <div className="flex flex-wrap gap-2">
                <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/40">
                  Active {activeCount}
                </span>
                <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-slate-800/90 text-slate-300 border border-slate-600">
                  Closed {closedCount}
                </span>
                <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/40">
                  Window 120d
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-400">
              Source: <a className="text-cyan-400 hover:text-cyan-300" href="https://eonet.gsfc.nasa.gov/api/v3/events" target="_blank" rel="noreferrer">EONET Events API</a>
            </p>
          </div>

          {loading ? (
            <div className="h-80 flex items-center justify-center">
              <div className="w-10 h-10 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
            </div>
          ) : events.length === 0 ? (
            <div className="h-80 rounded-2xl border border-cyan-500/25 bg-gradient-to-br from-cyan-500/10 via-slate-900/80 to-blue-950/50 relative overflow-hidden">
              <div className="absolute -top-20 -right-16 h-40 w-40 rounded-full bg-cyan-500/20 blur-2xl" />
              <div className="absolute -bottom-24 -left-20 h-48 w-48 rounded-full bg-indigo-500/20 blur-2xl" />
              <div className="h-full flex flex-col items-center justify-center text-center px-6">
                <div className="w-16 h-16 rounded-full border border-cyan-400/40 bg-cyan-500/10 flex items-center justify-center mb-4 animate-pulse">
                  <span className="text-2xl">📡</span>
                </div>
                <h3 className="text-lg font-semibold text-cyan-100">
                  {categoryHint === 'floods' ? 'No Flood Alerts In India' : 'No Urban/Manmade Alerts In India'}
                </h3>
                <p className="text-sm text-slate-300 mt-2 max-w-md">
                  {categoryHint === 'floods'
                    ? 'No live flood incidents were reported inside India for the selected monitoring window.'
                    : 'No live urban or manmade incidents were reported inside India for the selected monitoring window.'}
                </p>
                <p className="text-[11px] text-slate-400 mt-3">
                  {categoryHint === 'floods'
                    ? 'This confirms a calm flood situation right now.'
                    : 'Showing India activity radar below to keep this panel informative.'}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3 max-h-[560px] overflow-auto pr-1">
              {events.map((event) => {
                const latestGeom = event.geometry?.[event.geometry.length - 1]
                const when = formatEventTime(latestGeom?.date)
                const firstCategory = event.categories?.[0]?.title ?? 'Uncategorized'
                const freshness = getEventFreshness(latestGeom?.date)
                return (
                  <div key={event.id} className="border border-slate-700/80 rounded-xl p-4 bg-gradient-to-r from-slate-900/70 to-slate-900/30 hover:border-cyan-500/40 transition-colors">
                    <div className="flex items-start justify-between gap-4 mb-3">
                      <div className="min-w-0">
                        <div className="font-semibold text-white truncate">{event.title}</div>
                        <div className="text-xs text-slate-400 mt-1">{firstCategory}</div>
                      </div>
                      <a href={event.link} target="_blank" rel="noreferrer" className="text-xs text-cyan-400 hover:text-cyan-300 whitespace-nowrap">
                        Open event
                      </a>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2 py-1 rounded-md text-[11px] border border-slate-600 bg-slate-800/80 text-slate-300">
                        {when}
                      </span>
                      <span
                        className={cn(
                          "px-2 py-1 rounded-md text-[11px] border font-medium",
                          freshness === 'Breaking' && "border-rose-500/40 bg-rose-500/15 text-rose-200",
                          freshness === 'Active' && "border-amber-500/40 bg-amber-500/15 text-amber-200",
                          freshness === 'Historic' && "border-slate-600 bg-slate-800/80 text-slate-300"
                        )}
                      >
                        {freshness}
                      </span>
                      <span className={cn(
                        "px-2 py-1 rounded-md text-[11px] border font-medium",
                        event.closed == null
                          ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-200"
                          : "border-slate-600 bg-slate-800/80 text-slate-300"
                      )}>
                        {event.closed == null ? 'Open' : 'Closed'}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {showUrbanFallback && (
            <div className="mt-4 border border-slate-700/80 rounded-xl p-4 bg-slate-900/40">
              <div className="text-xs uppercase tracking-wide text-cyan-400 mb-3">India Activity Radar (Other Categories)</div>
              <div className="space-y-2 max-h-44 overflow-auto pr-1">
                {urbanFallbackEvents.map((event) => {
                  const latestGeom = event.geometry?.[event.geometry.length - 1]
                  return (
                    <div key={`fallback-${event.id}`} className="flex items-center justify-between gap-3 border border-slate-700 rounded-lg p-2.5">
                      <div className="min-w-0">
                        <div className="text-sm text-slate-200 truncate">{event.title}</div>
                        <div className="text-[11px] text-slate-400 truncate">{event.categories?.[0]?.title ?? 'Uncategorized'} • {formatEventTime(latestGeom?.date)}</div>
                      </div>
                      <a href={event.link} target="_blank" rel="noreferrer" className="text-[11px] text-cyan-400 hover:text-cyan-300 whitespace-nowrap">
                        Open
                      </a>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </GlassPanel>
      </div>

      <div className="lg:col-span-4">
        <GlassPanel className="p-6 h-full">
          <h3 className="font-display font-semibold text-white mb-2">Category Intelligence</h3>
          <div className="text-[11px] text-cyan-400 mb-3 uppercase tracking-wide">Linked EONET layers</div>
          <div className="text-xs text-slate-400 mb-4">
            {selectedCategory?.description ?? 'No category description available.'}
          </div>
          <div className="space-y-2 max-h-[500px] overflow-auto pr-1">
            {selectedLayers.length > 0 ? selectedLayers.map((layer) => (
              <div key={`${layer.name}-${layer.serviceUrl}`} className="p-3 rounded-lg border border-slate-700 bg-slate-900/50 hover:border-cyan-500/40 transition-colors">
                <div className="text-sm text-slate-200">{layer.name}</div>
                <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between gap-3">
                  <span>{layer.serviceTypeId}</span>
                  <span className="text-cyan-400">Live layer</span>
                </div>
              </div>
            )) : (
              <div className="text-sm text-slate-500">No layers listed for this category.</div>
            )}
          </div>
        </GlassPanel>
      </div>
    </motion.div>
  )
}

// ── Main export ──────────────────────────────────────────────────
export default function EarthObservatory() {
  const tabs = [
    { value: 'vegetation', label: '🌱 Vegetation' },
    { value: 'drought',    label: '💧 Drought' },
    { value: 'urban',      label: '🏙️ Urban' },
    { value: 'floods',     label: '🌊 Floods' }
  ]
  const [activeTab, setActiveTab] = useState('vegetation')
  const [geoData, setGeoData] = useState(null)

  useEffect(() => {
    fetch('/india-states.geojson')
      .then(res => res.json())
      .then(data => setGeoData(data))
      .catch(err => console.error('Failed to load GeoJSON', err))
  }, [])

  return (
    <div className="min-h-screen bg-[#0a0e17] text-slate-200 font-body">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-8 py-8">
        
        <div className="mb-8">
          <h1 className="text-3xl font-display font-bold text-white tracking-wide mb-2">Earth Observatory</h1>
          <p className="text-slate-400">Analyze geospatial data, track environmental changes, and predict impacts using satellite intelligence.</p>
        </div>

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
                    layoutId="earthTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.8)]"
                  />
                )}
              </button>
            )
          })}
        </div>

        <AnimatePresence mode="wait">
          {activeTab === 'vegetation' && <VegetationTab key="vegetation" geoData={geoData} />}
          {activeTab === 'drought'    && <DroughtTab    key="drought"    geoData={geoData} />}
          {activeTab === 'urban' && <EONETLiveTab key="urban-live" title="Urban/Manmade Events" categoryHint="manmade" />}
          {activeTab === 'floods' && <EONETLiveTab key="floods-live" title="Flood Monitoring" categoryHint="floods" />}
        </AnimatePresence>

      </div>
    </div>
  )
}
