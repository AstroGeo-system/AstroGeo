'use client'

import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import * as topojson from 'topojson-client'

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function toDms(deg) {
  const sign = deg < 0 ? -1 : 1
  const abs = Math.abs(deg)
  const d = Math.floor(abs)
  const minFloat = (abs - d) * 60
  const m = Math.floor(minFloat)
  const s = (minFloat - m) * 60
  return {
    d: d * sign,
    m,
    s,
  }
}

// ISRO centers used for markers and hover tooltip
const ISRO_CENTERS = [
  { name: 'Sriharikota', lat: 13.72, lng: 80.23 },
  { name: 'Thumba', lat: 8.52, lng: 76.86 },
]

function drawGlobe(ctx, globeState, marker, nightMode) {
  const { projection, path, land, graticule } = globeState
  if (!projection || !path || !land) return

  const { width, height } = ctx.canvas
  const dpr = window.devicePixelRatio || 1
  const w = width / dpr
  const h = height / dpr

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, w, h)

  const centerGeo = projection.invert([w / 2, h / 2])

  // Sphere / ocean
  ctx.save()
  ctx.beginPath()
  path.context(ctx)({ type: 'Sphere' })
  ctx.fillStyle = '#0ea5e9' // light ocean
  ctx.fill()
  ctx.clip()

  // Land
  ctx.beginPath()
  path(land)
  ctx.fillStyle = nightMode ? '#020617' : '#111827'
  ctx.shadowColor = 'rgba(0,0,0,0.6)'
  ctx.shadowBlur = 10
  ctx.fill()
  ctx.shadowBlur = 0

  // Graticule
  ctx.beginPath()
  path(graticule)
  ctx.strokeStyle = 'rgba(148,163,184,0.45)'
  ctx.lineWidth = 0.6
  ctx.setLineDash([4, 3])
  ctx.stroke()
  ctx.setLineDash([])

  // Red coordinate marker (back-face culled)
  if (marker) {
    const mGeo = [marker.lng, marker.lat]
    const front =
      centerGeo && d3.geoDistance(mGeo, centerGeo) < Math.PI / 2 - 0.02
    const proj = projection(mGeo)
    if (front && proj) {
      const [mx, my] = proj
      if (Number.isFinite(mx) && Number.isFinite(my)) {
        ctx.beginPath()
        ctx.arc(mx, my, 6, 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(248,113,113,0.9)'
        ctx.lineWidth = 2
        ctx.shadowColor = 'rgba(248,113,113,0.9)'
        ctx.shadowBlur = 14
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(mx, my, 3, 0, Math.PI * 2)
        ctx.fillStyle = '#ef4444'
        ctx.fill()
        ctx.shadowBlur = 0
      }
    }
  }

  // ISRO centers (back-face culled)
  ISRO_CENTERS.forEach((c) => {
    const geo = [c.lng, c.lat]
    const front =
      centerGeo && d3.geoDistance(geo, centerGeo) < Math.PI / 2 - 0.02
    const proj = projection(geo)
    if (!front || !proj) return
    const [x, y] = proj
    if (!Number.isFinite(x) || !Number.isFinite(y)) return

    const coreColor = nightMode ? '#facc15' : '#f97316'
    const glowColor = nightMode ? 'rgba(250,204,21,0.9)' : 'rgba(249,115,22,0.9)'

    ctx.beginPath()
    ctx.arc(x, y, 5, 0, Math.PI * 2)
    ctx.strokeStyle = coreColor
    ctx.lineWidth = 2
    ctx.shadowColor = glowColor
    ctx.shadowBlur = 12
    ctx.stroke()

    ctx.beginPath()
    ctx.arc(x, y, 2.5, 0, Math.PI * 2)
    ctx.fillStyle = coreColor
    ctx.fill()
    ctx.shadowBlur = 0
  })

  ctx.restore()
}

export default function AstroGlobeSearch({ className }) {
  const [marker, setMarker] = useState({ lat: 19.076, lng: 72.8777 }) // Mumbai
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [nightMode, setNightMode] = useState(false)
  const [hoveredCenter, setHoveredCenter] = useState(null)

  const containerRef = useRef(null)
  const canvasRef = useRef(null)
  const markerRef = useRef(marker)

  const globeRef = useRef({
    projection: null,
    path: null,
    land: null,
    graticule: d3.geoGraticule10(),
    currentRotate: [0, 0, 0],
    rafId: 0,
  })

  // init: load topojson, setup projection, drag, resize, hover
  useEffect(() => {
    let cancelled = false

    async function init() {
      try {
        const res = await fetch(
          'https://unpkg.com/world-atlas@2.0.2/countries-110m.json'
        )
        const topo = await res.json()
        const landFeature = topojson.feature(topo, topo.objects.countries)
        if (cancelled) return

        const projection = d3.geoOrthographic().precision(0.5).clipAngle(90)
        const path = d3.geoPath(projection)
        globeRef.current.projection = projection
        globeRef.current.path = path
        globeRef.current.land = landFeature

        const resizeAndDraw = () => {
          const container = containerRef.current
          const canvas = canvasRef.current
          if (!container || !canvas || !projection) return
          const { width, height } = container.getBoundingClientRect()
          const dpr = window.devicePixelRatio || 1
          canvas.width = width * dpr
          canvas.height = height * dpr
          canvas.style.width = `${width}px`
          canvas.style.height = `${height}px`
          const ctx = canvas.getContext('2d')
          const scale = Math.min(width, height) * 0.46
          projection.translate([width / 2, height / 2]).scale(scale)
          drawGlobe(ctx, globeRef.current, markerRef.current, nightMode)
        }

        resizeAndDraw()
        setLoading(false)

        const canvas = canvasRef.current
        if (canvas) {
          // drag rotation
          const drag = d3
            .drag()
            .on('start', (event) => {
              globeRef.current.dragStart = {
                x: event.x,
                y: event.y,
                rotate: globeRef.current.currentRotate.slice(),
              }
            })
            .on('drag', (event) => {
              const start = globeRef.current.dragStart
              if (!start) return
              const sensitivity = 0.25
              const dx = event.x - start.x
              const dy = event.y - start.y
              const lon = start.rotate[0] + dx * sensitivity
              const lat = clamp(start.rotate[1] - dy * sensitivity, -85, 85)
              const r = [lon, lat, 0]
              globeRef.current.currentRotate = r
              projection.rotate(r)
              const ctx = canvas.getContext('2d')
              if (ctx) drawGlobe(ctx, globeRef.current, markerRef.current, nightMode)
            })
            .on('end', () => {
              globeRef.current.dragStart = null
            })

          d3.select(canvas).call(drag)

          // hover detection over ISRO centers
          const handleMove = (ev) => {
            const rect = canvas.getBoundingClientRect()
            const x = ev.clientX - rect.left
            const y = ev.clientY - rect.top
            const proj = globeRef.current.projection
            if (!proj) return

            const dpr = window.devicePixelRatio || 1
            const w = canvas.width / dpr
            const h = canvas.height / dpr
            const centerGeo = proj.invert([w / 2, h / 2])

            let found = null
            let minDist = Infinity
            ISRO_CENTERS.forEach((c) => {
              const geo = [c.lng, c.lat]
              const front =
                centerGeo && d3.geoDistance(geo, centerGeo) < Math.PI / 2 - 0.02
              const p = proj(geo)
              if (!front || !p) return
              const [cx, cy] = p
              const dx = cx - x
              const dy = cy - y
              const dist = Math.sqrt(dx * dx + dy * dy)
              if (dist <= 10 && dist < minDist) {
                minDist = dist
                found = {
                  name: c.name,
                  lat: c.lat,
                  lng: c.lng,
                  x,
                  y,
                }
              }
            })

            setHoveredCenter(found)
          }

          canvas.addEventListener('mousemove', handleMove)

          // cleanup listeners
          const resizeObserver = new ResizeObserver(resizeAndDraw)
          if (containerRef.current) resizeObserver.observe(containerRef.current)

          return () => {
            resizeObserver.disconnect()
            canvas.removeEventListener('mousemove', handleMove)
          }
        }
      } catch (e) {
        console.error('Failed to load world atlas', e)
        setLoading(false)
      }
    }

    const cleanup = init()

    return () => {
      cancelled = true
      if (globeRef.current.rafId) cancelAnimationFrame(globeRef.current.rafId)
      if (typeof cleanup === 'function') cleanup()
    }
  }, [nightMode])

  // keep markerRef in sync with state
  useEffect(() => {
    markerRef.current = marker
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (ctx) drawGlobe(ctx, globeRef.current, marker, nightMode)
  }, [marker.lat, marker.lng, nightMode])

  // smooth rotation to center new marker
  useEffect(() => {
    const { projection } = globeRef.current
    const canvas = canvasRef.current
    if (!projection || !canvas) return

    const ctx = canvas.getContext('2d')
    const startRotate = globeRef.current.currentRotate
    const endRotate = [-marker.lng, -marker.lat, 0]
    const interp = d3.interpolate(startRotate, endRotate)

    const duration = 800
    const start = performance.now()

    const animate = (now) => {
      const t = Math.min(1, (now - start) / duration)
      const r = interp(t)
      projection.rotate(r)
      globeRef.current.currentRotate = r

      if (ctx) drawGlobe(ctx, globeRef.current, markerRef.current, nightMode)

      if (t < 1) {
        globeRef.current.rafId = requestAnimationFrame(animate)
      }
    }

    globeRef.current.rafId = requestAnimationFrame(animate)
  }, [marker.lat, marker.lng, nightMode])

  const latDms = toDms(marker.lat)
  const lngDms = toDms(marker.lng)

  const handleLatChange = (val) => {
    const v = clamp(Number(val) || 0, -90, 90)
    setMarker((m) => ({ ...m, lat: v }))
  }

  const handleLngChange = (val) => {
    const v = clamp(Number(val) || 0, -180, 180)
    setMarker((m) => ({ ...m, lng: v }))
  }

  const handleSearchKeyDown = async (event) => {
    if (event.key !== 'Enter') return
    const query = search.trim()
    if (!query) return
    try {
      const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(
        query
      )}&format=json&limit=1`
      const res = await fetch(url, {
        headers: { 'Accept-Language': 'en' },
      })
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        const { lat, lon, display_name } = data[0]
        const latNum = parseFloat(lat)
        const lngNum = parseFloat(lon)
        if (Number.isFinite(latNum) && Number.isFinite(lngNum)) {
          setMarker({ lat: latNum, lng: lngNum })
          // optional: show in tooltip later using hoveredCenter if desired
        }
      }
    } catch (e) {
      console.error('Nominatim lookup failed', e)
    }
  }

  return (
    <div className={cn('glass rounded-3xl p-4 lg:p-5', className)}>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Globe area */}
        <div className="lg:col-span-8 relative">
          {/* Floating search bar */}
          <div className="pointer-events-none absolute left-4 top-4 z-10 w-[260px]">
            <div className="pointer-events-auto glass px-3 py-2 rounded-2xl flex items-center gap-2">
              <span className="text-slate-500 text-sm">⌕</span>
              <input
                className="w-full bg-transparent outline-none text-xs text-slate-200 placeholder:text-slate-600"
                placeholder="Search place or coordinates"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleSearchKeyDown}
              />
            </div>
          </div>

          <div
            ref={containerRef}
            className="relative h-[420px] sm:h-[460px] lg:h-[520px] overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-sky-500/40 via-sky-600/40 to-slate-900"
          >
            <canvas ref={canvasRef} className="absolute inset-0" />
            {loading && (
              <div className="absolute inset-0 grid place-items-center">
                <div className="glass px-4 py-3 rounded-2xl text-sm text-slate-200">
                  Loading globe…
                </div>
              </div>
            )}
            {hoveredCenter && (
              <div
                className="pointer-events-none absolute z-20 glass px-3 py-2 rounded-2xl text-xs text-slate-100"
                style={{
                  left: hoveredCenter.x + 12,
                  top: hoveredCenter.y + 12,
                }}
              >
                <div className="font-medium">{hoveredCenter.name}</div>
                <div className="text-[11px] text-slate-300 mt-0.5">
                  Lat {hoveredCenter.lat.toFixed(2)}°, Lng{' '}
                  {hoveredCenter.lng.toFixed(2)}°
                </div>
                <div className="text-[11px] text-emerald-400 mt-0.5">
                  Status: Active
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Side panel */}
        <div className="lg:col-span-4 space-y-4">
          <div className="glass rounded-2xl p-4 space-y-4">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs uppercase tracking-wider text-slate-500">
                Input Coordinates
              </div>
              <button
                type="button"
                onClick={() => setNightMode((v) => !v)}
                className="text-[11px] px-2 py-1 rounded-xl bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 transition"
              >
                Night mode: <span className="font-mono">{nightMode ? 'ON' : 'OFF'}</span>
              </button>
            </div>
            <div className="mt-1 text-sm text-slate-300">
                Move sliders or type values to reposition the red marker in real time.
              </div>
            </div>

            {/* Latitude */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Latitude</span>
                <span className="font-mono text-slate-200">{marker.lat.toFixed(3)}°</span>
              </div>
              <input
                type="range"
                min={-90}
                max={90}
                step={0.01}
                value={marker.lat}
                onChange={(e) => handleLatChange(e.target.value)}
                className="w-full accent-cyan-300"
              />
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={-90}
                  max={90}
                  step={0.01}
                  value={marker.lat}
                  onChange={(e) => handleLatChange(e.target.value)}
                  className="w-28 rounded-xl bg-white/5 border border-white/10 px-2 py-1 text-xs text-slate-100 outline-none"
                />
                <span className="text-xs text-slate-500">-90 (S) to 90 (N)</span>
              </div>
            </div>

            {/* Longitude */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Longitude</span>
                <span className="font-mono text-slate-200">{marker.lng.toFixed(3)}°</span>
              </div>
              <input
                type="range"
                min={-180}
                max={180}
                step={0.01}
                value={marker.lng}
                onChange={(e) => handleLngChange(e.target.value)}
                className="w-full accent-cyan-300"
              />
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={-180}
                  max={180}
                  step={0.01}
                  value={marker.lng}
                  onChange={(e) => handleLngChange(e.target.value)}
                  className="w-28 rounded-xl bg-white/5 border border-white/10 px-2 py-1 text-xs text-slate-100 outline-none"
                />
                <span className="text-xs text-slate-500">-180 (W) to 180 (E)</span>
              </div>
            </div>
          </div>

          {/* DD → DMS converter */}
          <div className="glass rounded-2xl p-4">
            <div className="text-xs uppercase tracking-wider text-slate-500 mb-3">
              DD → DMS Converter
            </div>
            <table className="w-full text-xs text-slate-300">
              <thead className="text-slate-500">
                <tr>
                  <th className="text-left pb-1">Coord</th>
                  <th className="text-left pb-1">Decimal (DD)</th>
                  <th className="text-left pb-1">DMS</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-white/10">
                  <td className="py-1.5 pr-2 text-slate-400">Lat</td>
                  <td className="py-1.5 pr-2 font-mono">
                    {marker.lat.toFixed(5)}
                  </td>
                  <td className="py-1.5 font-mono text-[11px]">
                    {`${latDms.d}° ${latDms.m}' ${latDms.s.toFixed(2)}"`}
                  </td>
                </tr>
                <tr className="border-t border-white/10">
                  <td className="py-1.5 pr-2 text-slate-400">Lng</td>
                  <td className="py-1.5 pr-2 font-mono">
                    {marker.lng.toFixed(5)}
                  </td>
                  <td className="py-1.5 font-mono text-[11px]">
                    {`${lngDms.d}° ${lngDms.m}' ${lngDms.s.toFixed(2)}"`}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
  )
}


