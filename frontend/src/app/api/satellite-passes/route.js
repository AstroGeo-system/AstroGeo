import { NextResponse } from 'next/server'

export const runtime = 'nodejs'

// Generates mock ISS passes that are consistent for the current day
function generateMockPasses(lat, days = 7) {
  // Use start of current UTC day as the stable anchor instead of dynamic Date.now()
  const d = new Date()
  d.setUTCHours(0, 0, 0, 0)
  const baseAnchor = Math.floor(d.getTime() / 1000)
  const passes = []

  for (let i = 0; i < Math.min(5, days * 1); i++) {
    // Generate passes starting from the anchor, so they remain stable throughout today
    // Offset them so some might have already happened today, and some are in the future
    const offset = 3600 * ((i * 12) + 8) // E.g., 8 AM, 8 PM, etc.
    const duration = 300 + i * 60 // 5-10 min passes
    const maxEl = [65, 42, 28, 51, 33][i % 5]
    passes.push({
      startUTC: baseAnchor + offset,
      endUTC: baseAnchor + offset + duration,
      startAz: (150 + i * 55) % 360,
      endAz: (30 + i * 40) % 360,
      maxEl,
    })
  }
  return passes
}

export async function GET(request) {
  const { searchParams } = new URL(request.url)
  const satId = searchParams.get('satId')
  const lat   = searchParams.get('lat')
  const lng   = searchParams.get('lng')
  const alt   = searchParams.get('alt') || '0'
  const days  = searchParams.get('days')
  const minEl = searchParams.get('minElevation')

  if (!satId || !lat || !lng || !days || !minEl) {
    return NextResponse.json({ error: 'Missing required parameters' }, { status: 400 })
  }

  const apiKey = process.env.N2YO_API_KEY

  // No API key → immediately return realistic mock passes
  if (!apiKey || apiKey === 'dummy_key' || apiKey === '') {
    const mockPasses = generateMockPasses(parseFloat(lat), parseInt(days, 10))
    return NextResponse.json({
      info:   { passescount: mockPasses.length },
      passes: mockPasses,
      source: 'mock',
    })
  }

  // Try live N2YO
  try {
    const url = `https://api.n2yo.com/rest/v1/satellite/visualpasses/${satId}/${lat}/${lng}/${alt}/${days}/${minEl}?apiKey=${apiKey}`
    const response = await fetch(url, { next: { revalidate: 0 } })
    const text = await response.text()

    let data
    try {
      data = JSON.parse(text)
    } catch {
      data = { error: 'Invalid N2YO response' }
    }

    if (data.error) {
      throw new Error(data.error)
    }

    // N2YO uses specific field names — normalise to unified shape
    const normalised = (data.passes || []).map(p => ({
      startUTC: p.startUTC,
      endUTC:   p.endUTC,
      startAz:  p.startAz,
      endAz:    p.endAz,
      maxEl:    p.maxEl,
    }))

    return NextResponse.json({ info: data.info, passes: normalised, source: 'live' })
  } catch (err) {
    // Live failed → fall back to mock
    const mockPasses = generateMockPasses(parseFloat(lat), parseInt(days, 10))
    return NextResponse.json({
      info:   { passescount: mockPasses.length },
      passes: mockPasses,
      source: 'mock_fallback',
      note:   `N2YO unavailable: ${err.message}`,
    })
  }
}
