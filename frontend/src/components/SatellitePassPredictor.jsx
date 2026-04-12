'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useAppShell } from '@/components/providers/AppShellProvider'

const CITIES = {
  'Mumbai, MH': [19.0760, 72.8777],
  'Delhi, NCR': [28.7041, 77.1025],
  'Bengaluru, KA': [12.9716, 77.5946],
  'Chennai, TN': [13.0827, 80.2707],
  'Kolkata, WB': [22.5726, 88.3639],
  'Hyderabad, TS': [17.3850, 78.4867]
}

const SATELLITES = {
  'ISS': 25544,
  // Add more if needed
}

function GlassPanel({ children, className }) {
  return (
    <div className={`bg-[#111827]/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden ${className}`}>
      {children}
    </div>
  )
}

function formatTime(timestamp) {
  return new Date(timestamp * 1000).toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  })
}

function formatDate(timestamp) {
  return new Date(timestamp * 1000).toLocaleDateString('en-IN', {
    month: 'short',
    day: 'numeric'
  })
}

function getDirection(azimuth) {
  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
  return directions[Math.round(azimuth / 22.5) % 16]
}

function getVisibilityRating(maxElevation) {
  if (maxElevation >= 60) return { label: 'EXCELLENT', color: 'text-emerald-400', icon: '✅' }
  if (maxElevation >= 40) return { label: 'GOOD', color: 'text-blue-400', icon: '👍' }
  if (maxElevation >= 20) return { label: 'FAIR', color: 'text-yellow-400', icon: '⚠️' }
  return { label: 'POOR', color: 'text-red-400', icon: '❌' }
}

function mockAIConfidence(pass) {
  // Mock based on elevation and time
  const elevation = pass.maxElevation
  const now = Date.now() / 1000
  const timeDiff = Math.abs(pass.startTime - now)
  let confidence = 50 + (elevation / 90) * 40 - (timeDiff / 86400) * 10 // Rough mock
  confidence = Math.max(10, Math.min(95, confidence))
  return Math.round(confidence)
}

export default function SatellitePassPredictor() {
  const { homeCity } = useAppShell()
  const [location, setLocation] = useState(homeCity)
  const [satellite, setSatellite] = useState('ISS')
  const [dateRange, setDateRange] = useState('7')
  const [filters, setFilters] = useState({
    visibleOnly: true,
    minElevation: 30,
    nightOnly: false
  })
  const [passes, setPasses] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchPasses = async () => {
    setLoading(true)
    setError(null)
    try {
      const [lat, lng] = CITIES[location] || [19.0760, 72.8777] // Default to Mumbai
      const satId = SATELLITES[satellite]
      const params = new URLSearchParams({
        satId: satId.toString(),
        lat: lat.toString(),
        lng: lng.toString(),
        days: dateRange,
        minElevation: filters.minElevation.toString()
      })
      const url = `/api/satellite-passes?${params}`
      
      const response = await fetch(url)
      const data = await response.json()
      
      if (data.error) {
        throw new Error(data.error)
      }
      
      setPasses(data.passes || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPasses()
  }, [location, satellite, dateRange, filters])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-6"
    >
      <GlassPanel className="p-6">
        <h2 className="text-xl font-display font-semibold text-white mb-6 flex items-center gap-2">
          🔮 SATELLITE PASS PREDICTOR
        </h2>

        {/* Form */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">📍 Your Location</label>
            <select
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-2 outline-none focus:border-cyan-500/50"
            >
              {Object.keys(CITIES).map(city => (
                <option key={city} value={city}>{city}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">🛰️ Select Satellite</label>
            <select
              value={satellite}
              onChange={(e) => setSatellite(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-2 outline-none focus:border-cyan-500/50"
            >
              {Object.keys(SATELLITES).map(sat => (
                <option key={sat} value={sat}>{sat}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">📅 Date Range</label>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="w-full bg-slate-900/50 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-2 outline-none focus:border-cyan-500/50"
            >
              <option value="1">Today</option>
              <option value="3">Next 3 days</option>
              <option value="7">Next 7 days</option>
              <option value="14">Next 14 days</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">⚙️ Filters</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={filters.visibleOnly}
                  onChange={(e) => setFilters(prev => ({ ...prev, visibleOnly: e.target.checked }))}
                  className="rounded"
                />
                Only visible passes
              </label>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Min elevation:</span>
                <select
                  value={filters.minElevation}
                  onChange={(e) => setFilters(prev => ({ ...prev, minElevation: parseInt(e.target.value) }))}
                  className="bg-slate-900/50 border border-slate-700 text-slate-300 text-xs rounded px-2 py-1"
                >
                  <option value="10">10°</option>
                  <option value="20">20°</option>
                  <option value="30">30°</option>
                  <option value="40">40°</option>
                  <option value="50">50°</option>
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={filters.nightOnly}
                  onChange={(e) => setFilters(prev => ({ ...prev, nightOnly: e.target.checked }))}
                  className="rounded"
                />
                Night passes only
              </label>
            </div>
          </div>
        </div>

        <button
          onClick={fetchPasses}
          disabled={loading}
          className="w-full bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-600 text-white font-medium py-2 px-4 rounded-lg transition-colors"
        >
          {loading ? '🔍 Searching...' : '🔍 Find Passes'}
        </button>

        {/* Results */}
        <div className="mt-6">
          <h3 className="text-lg font-semibold text-white mb-4">📊 UPCOMING VISIBLE PASSES ({location})</h3>
          
          {error && (
            <div className="text-red-400 text-sm mb-4">
              Error: {error}
            </div>
          )}

          {passes.length === 0 && !loading && !error && (
            <div className="text-slate-400 text-sm">
              No passes found for the selected criteria.
            </div>
          )}

          <div className="space-y-4 max-h-96 overflow-y-auto">
            {passes.map((pass, index) => {
              const visibility = getVisibilityRating(pass.maxElevation)
              const aiConfidence = mockAIConfidence(pass)
              const startDate = formatDate(pass.startTime)
              const startTime = formatTime(pass.startTime)
              const endTime = formatTime(pass.endTime)
              const riseDir = getDirection(pass.startAz)
              const setDir = getDirection(pass.endAz)

              return (
                <div key={index} className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div className="text-sm font-bold text-white">
                      {startDate} - {startTime}
                    </div>
                    <div className={`inline-block px-2 py-1 rounded text-xs font-bold uppercase tracking-wider ${visibility.color} border border-current/30`}>
                      {visibility.icon} {visibility.label}
                    </div>
                  </div>
                  
                  <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/50 mb-3">
                    <div className="text-xs text-slate-400 mb-1">
                      Rise: {startTime} ({riseDir}) → Set: {endTime} ({setDir})
                    </div>
                    <div className="text-xs text-slate-400">
                      Max Elevation: {pass.maxElevation}° | Duration: {Math.round((pass.endTime - pass.startTime) / 60)} min
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="text-xs text-cyan-400 font-medium">
                      🤖 AI Confidence: {aiConfidence}% (Mock prediction)
                    </div>
                    <div className="flex gap-2">
                      <button className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded">
                        🔔 Set Reminder
                      </button>
                      <button className="text-xs bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded">
                        📅 Add to Calendar
                      </button>
                      <button className="text-xs bg-emerald-700 hover:bg-emerald-600 px-2 py-1 rounded">
                        ✅ Verify Prediction
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </GlassPanel>
    </motion.div>
  )
}