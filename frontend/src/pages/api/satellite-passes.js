export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { satId, lat, lng, alt = '0', days, minElevation } = req.query

  if (!satId || !lat || !lng || !days || !minElevation) {
    return res.status(400).json({ error: 'Missing required parameters' })
  }

  try {
    const apiKey = process.env.N2YO_API_KEY || 'dummy_key'
    const url = `https://api.n2yo.com/rest/v1/satellite/visualpasses/${satId}/${lat}/${lng}/${alt}/${days}/${minElevation}?apiKey=${apiKey}`
    const response = await fetch(url)
    const text = await response.text()
    
    let data;
    try {
      data = JSON.parse(text)
    } catch (e) {
      return res.status(503).json({ error: 'N2YO API unavailable', detail: 'Received invalid response from N2YO.' })
    }

    if (data.error) {
      return res.status(503).json({ error: 'N2YO API unavailable', detail: data.error })
    }

    res.status(200).json(data)
  } catch (error) {
    res.status(503).json({ error: 'N2YO API unavailable', detail: error.message })
  }
}
