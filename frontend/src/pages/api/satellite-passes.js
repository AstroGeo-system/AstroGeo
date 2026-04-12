export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  const { satId, lat, lng, alt = '0', days, minElevation } = req.query

  if (!satId || !lat || !lng || !days || !minElevation) {
    return res.status(400).json({ error: 'Missing required parameters' })
  }

  try {
    const apiKey = 'api key'
    const url = `https://api.n2yo.com/rest/v1/satellite/visualpasses/${satId}/${lat}/${lng}/${alt}/${days}/${minElevation}?apiKey=${apiKey}`
    const response = await fetch(url)
    const data = await response.json()

    res.status(200).json(data)
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch data' })
  }
}
