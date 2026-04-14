// src/lib/api.js
// Central API client — all calls to the AstroGeo FastAPI backend.

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function get(path) {
  try {
    const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
    if (!res.ok) return null
    return res.json()
  } catch (e) {
    console.warn(`[API] GET ${path} failed:`, e.message)
    return null
  }
}

async function post(path, body) {
  try {
    const res = await fetch(`${BASE}${path}`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
      cache:   'no-store',
    })
    return res.json()
  } catch (e) {
    console.warn(`[API] POST ${path} failed:`, e.message)
    return null
  }
}

export const api = {
  // ── Stats ticker (parallel fetch) ──────────────────────────
  getLiveStats: () =>
    Promise.all([
      get('/api/launch/schedule'),
      get('/api/v1/iss/passes'),
      get('/api/verify/batch/recent?limit=5'),
    ]),

  // ── ISS ───────────────────────────────────────────────────
  getISSPasses: () => get('/api/v1/iss/passes'),

  // ── Asteroids ─────────────────────────────────────────────
  getAlerts:    () => get('/api/asteroids/alerts'),
  getClusters:  () => get('/api/asteroids/clusters'),
  getAnomalies: () => get('/api/asteroids/anomalies'),
  getAsteroid:  (des) => get(`/api/asteroids/${des}`),

  // ── Earth Watch ───────────────────────────────────────────
  getNDVI:      (zone, year = 2024) => get(`/api/earth/ndvi/${zone}?year=${year}`),
  getChange:    (zone) => get(`/api/earth/change/${zone}`),
  getLiveNDVI:  (zone, year) => get(`/api/earth/live/${zone}/${year}`),
  getEONETEvents: (params = '') => get(`/api/eonet/events${params ? `?${params}` : ''}`),
  getEONETGeoJSON: (params = '') => get(`/api/eonet/events/geojson${params ? `?${params}` : ''}`),
  getEONETCategories: () => get('/api/eonet/categories'),
  getEONETLayers: () => get('/api/eonet/layers'),

  // ── Agriculture ───────────────────────────────────────────
  getDrought:   (district) => get(`/api/agro/drought/${district}`),
  getYield:     (crop, district) => get(`/api/agro/yield/${crop}/${district}`),
  getPrices:    (market) => get(`/api/agro/prices/${market}`),

  // ── Launch ────────────────────────────────────────────────
  getLaunchProb:     () => get('/api/launch/probability'),
  getLaunchSchedule: () => get('/api/launch/schedule'),
  
  // ── ISRO tracker ──────────────────────────────────────────
  getIsroFleet:      () => get('/api/isro/fleet'),

  // ── GraphRAG ──────────────────────────────────────────────
  query: (q) =>
    post('/api/graph/query', { query: q, include_evidence: true }),

  // ── Verification ──────────────────────────────────────────
  verify:        (id)     => get(`/api/verify/${id}`),
  verifyBatch:   (n = 10) => get(`/api/verify/batch/recent?limit=${n}`),
  getModelCards: ()       => get('/api/verify/model-cards'),

  // ── Solar Risk & Events ───────────────────────────────────
  getSolarRisk:   () => get('/api/launch/solar-risk'),
  getSolarEvents: () => get('/api/v1/donki/events'),

  // ── Chat (OpenAI proxy) ───────────────────────────────────
  chat: (messages, user_query) =>
    post('/api/chat', { messages, user_query }),
}
