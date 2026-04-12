export default async function handler(req, res) {
  const { days = '90', agencies = '' } = req.query
  const selectedAgencies = agencies
    .split(',')
    .map((agency) => agency.trim())
    .filter(Boolean)

  try {
    const endDate = new Date()
    endDate.setDate(endDate.getDate() + Number(days))
    const url = `https://ll.thespacedevs.com/2.2.0/launch/upcoming/?window_start__lte=${encodeURIComponent(
      endDate.toISOString()
    )}&limit=12`

    const response = await fetch(url)
    if (!response.ok) throw new Error(`Launch Library ${response.status}`)
    const data = await response.json()
    let launches = data.results || []

    if (selectedAgencies.length > 0 && !selectedAgencies.includes('All Agencies')) {
      const normalized = selectedAgencies.map((name) => name.toLowerCase())
      launches = launches.filter((launch) => {
        const provider = launch.launch_service_provider?.name?.toLowerCase() || ''
        const isKnownAgency = normalized.some((agency) => provider.includes(agency))
        if (normalized.includes('others')) return !['isro', 'spacex', 'nasa'].some((tag) => provider.includes(tag))
        return isKnownAgency
      })
    }

    res.status(200).json({ launches })
  } catch (error) {
    res.status(500).json({ error: error.message || 'Failed to fetch Launch Library data' })
  }
}
