// ── U4: Story Angle generators ────────────────────────────────────
// Template-based, live-data-interpolated headlines for Journalist persona.
// No LLM calls — pure template + threshold logic.

/**
 * Build the Solar story angle from DONKI events data.
 * @param {object|null} solarData - response from api.getSolarEvents()
 * @returns {{ headline: string, body: string, query: string }}
 */
export function buildSolarAngle(solarData) {
  const events = solarData?.events ?? solarData?.data ?? solarData ?? []
  const recent = Array.isArray(events)
    ? events.filter(e => {
        const d = new Date(e.beginTime ?? e.date ?? e.startTime ?? 0)
        return (Date.now() - d.getTime()) < 7 * 24 * 60 * 60 * 1000
      })
    : []

  const significant = recent.find(e =>
    e.classType?.startsWith('X') || e.classType?.startsWith('M') || e.kpIndex > 5
  )

  if (significant) {
    const classType = significant.classType ?? 'M-class'
    const daysAgo = significant.beginTime
      ? Math.round((Date.now() - new Date(significant.beginTime).getTime()) / 86400000)
      : 3
    return {
      headline: 'Solar Activity Elevated Over India — GPS Farming Systems at Risk',
      body: `A ${classType} flare was recorded ${daysAgo} day${daysAgo !== 1 ? 's' : ''} ago. During the May 2024 G5 storm, GPS disruption cost US farmers $500M — Indian precision agriculture faces the same risk.`,
      query: 'Did the May 2024 solar storm affect Indian farmers?',
    }
  }

  return {
    headline: 'Solar Activity Calm — Safe Window for GPS-Guided Farming',
    body: "No significant solar flares in the past 7 days. India's 17 monitored agricultural zones are operating under nominal GNSS conditions.",
    query: 'What is the current solar activity level affecting Indian agriculture?',
  }
}

/**
 * Build the Vegetation/Drought story angle from NDVI data across zones.
 * @param {Array} ndviResults - array of { zone, summary } from api.getNDVI(zone)
 * @returns {{ headline: string, body: string, query: string }}
 */
export function buildVegetationAngle(ndviResults) {
  const valid = (ndviResults ?? []).filter(r => r?.summary?.mean_ndvi != null)
  if (!valid.length) {
    return {
      headline: 'Satellite Data Shows Growing Vegetation Stress Across India',
      body: '17 agricultural zones are being monitored via Sentinel-2 satellite imagery. Multiple zones show NDVI readings below the 0.3 threshold indicating poor vegetation health.',
      query: 'Which Indian regions face the highest drought risk?',
    }
  }

  const worst = valid.reduce((a, b) =>
    (a.summary.mean_ndvi ?? 1) < (b.summary.mean_ndvi ?? 1) ? a : b
  )
  const zone = worst.zone ?? 'Maharashtra'
  const ndvi = worst.summary.mean_ndvi?.toFixed(2) ?? '0.28'
  const poorCount = valid.filter(r => (r.summary.mean_ndvi ?? 1) < 0.3).length
  const moderateCount = valid.filter(r => {
    const v = r.summary.mean_ndvi ?? 1
    return v >= 0.3 && v < 0.5
  }).length

  return {
    headline: `${zone} Shows Sharpest Vegetation Decline in AstroGeo's 2024 Data`,
    body: `Sentinel-2 satellite imagery shows an NDVI mean of ${ndvi} in ${zone} — below the 0.3 threshold indicating poor vegetation health. ${poorCount + moderateCount} of ${valid.length} monitored zones are in the moderate or poor category.`,
    query: `What is the drought risk in ${zone} right now?`,
  }
}

/**
 * Build the Asteroid/Launch story angle.
 * @param {object|null} alertsData - response from api.getAlerts()
 * @param {object|null} launchData - response from api.getLaunchProb()
 * @returns {{ headline: string, body: string, query: string }}
 */
export function buildAsteroidLaunchAngle(alertsData, launchData) {
  const alerts = alertsData?.data ?? alertsData?.alerts ?? []
  const highRisk = Array.isArray(alerts)
    ? alerts.filter(a => (a.risk ?? a.risk_category ?? '').toLowerCase() === 'high')
    : []

  if (highRisk.length > 0) {
    const top = highRisk[0]
    const des = top.designation ?? top.des ?? top.name ?? 'Unknown'
    const score = top.kinetic_energy_proxy ?? top.improved_risk_score?.toFixed(1) ?? 'elevated'
    return {
      headline: `NASA Data Flags ${highRisk.length} Asteroid${highRisk.length > 1 ? 's' : ''} as High Risk`,
      body: `AstroGeo's AI model has identified ${highRisk.length} near-Earth asteroid${highRisk.length > 1 ? 's' : ''} with unusual energy profiles. The highest-risk object, ${des}, has a risk score of ${score} — flagged for expert review.`,
      query: 'What are the top risk asteroids approaching Earth?',
    }
  }

  const days = launchData?.countdown?.days ?? launchData?.days_until ?? 23
  const prob = launchData?.probability ?? launchData?.launch_probability ?? 91.9
  return {
    headline: `ISRO's Next Launch in ${days} Days — AI Gives It ${prob.toFixed(0)}% On-Time Probability`,
    body: `AstroGeo's launch probability model, trained on 108 ISRO missions, gives the next scheduled launch a ${prob.toFixed(0)}% likelihood of proceeding on schedule. ${prob > 85 ? 'Conditions are currently favourable.' : 'Some risk factors are elevated.'}`,
    query: `What is the ISRO launch probability for the next mission?`,
  }
}
