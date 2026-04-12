export default async function handler(req, res) {
  const { days = '30', distanceAU = '0.2', minDiameter = '100' } = req.query

  const apiKey = process.env.NASA_API_KEY || 'DEMO_KEY'
  const startDate = new Date()
  const endDate = new Date(startDate)
  endDate.setDate(endDate.getDate() + Number(days))

  const generateChunks = () => {
    const chunks = []
    let cursor = new Date(startDate)
    while (cursor <= endDate) {
      const chunkEnd = new Date(cursor)
      chunkEnd.setDate(chunkEnd.getDate() + 6)
      if (chunkEnd > endDate) chunkEnd.setTime(endDate.getTime())
      const start = cursor.toISOString().split('T')[0]
      const end = chunkEnd.toISOString().split('T')[0]
      chunks.push({ start, end })
      cursor = new Date(chunkEnd)
      cursor.setDate(cursor.getDate() + 1)
    }
    return chunks
  }

  try {
    const chunks = generateChunks()
    const responses = await Promise.all(
      chunks.map(({ start, end }) =>
        fetch(`https://api.nasa.gov/neo/rest/v1/feed?start_date=${start}&end_date=${end}&api_key=${apiKey}`).then((r) => {
          if (!r.ok) throw new Error(`NeoWS ${r.status}`)
          return r.json()
        })
      )
    )

    const maxDistance = Number(distanceAU)
    const minDiameterMeters = Number(minDiameter)
    const approaches = []

    for (const data of responses) {
      const objects = data.near_earth_objects || {}
      for (const dateKey of Object.keys(objects)) {
        const list = objects[dateKey]
        for (const neo of list) {
          const diameterMeters = neo.estimated_diameter?.meters
          const diameterValue = diameterMeters?.estimated_diameter_max ?? diameterMeters?.estimated_diameter_min ?? 0
          for (const approach of neo.close_approach_data || []) {
            if (approach.orbiting_body !== 'Earth') continue
            const distance = Number(approach.miss_distance?.astronomical)
            if (Number.isNaN(distance) || distance > maxDistance) continue
            if (diameterValue < minDiameterMeters) continue

            approaches.push({
              id: `${neo.id}-${approach.close_approach_date}`,
              name: neo.name,
              date: approach.close_approach_date,
              epochDate: approach.epoch_date_close_approach,
              distanceAU: distance.toFixed(3),
              distanceKm: Number(distance * 149597870.7).toLocaleString(undefined, { maximumFractionDigits: 0 }),
              diameter: Math.round(diameterValue),
              velocity: Number(approach.relative_velocity?.kilometers_per_second || 0).toFixed(1),
              magnitude: neo.absolute_magnitude_h != null ? Number(neo.absolute_magnitude_h).toFixed(1) : '—',
              orbitingBody: approach.orbiting_body,
            })
          }
        }
      }
    }

    approaches.sort((a, b) => a.epochDate - b.epochDate)

    res.status(200).json({ approaches })
  } catch (error) {
    res.status(500).json({ error: error.message || 'Failed to fetch NeoWs data' })
  }
}
