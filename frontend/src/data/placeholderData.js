// Placeholder satellite and mission data for the dashboard

export const satellites = [
  { id: 'SAT-001', name: 'Cartosat-3', orbit: 'SSO', altitude: 509, status: 'active', lastUpdate: '2 min ago' },
  { id: 'SAT-002', name: 'RISAT-2B', orbit: 'LEO', altitude: 557, status: 'active', lastUpdate: '5 min ago' },
  { id: 'SAT-003', name: 'GSAT-30', orbit: 'GEO', altitude: 35786, status: 'active', lastUpdate: '1 min ago' },
  { id: 'SAT-004', name: 'Resourcesat-2', orbit: 'SSO', altitude: 817, status: 'active', lastUpdate: '3 min ago' },
  { id: 'SAT-005', name: 'INSAT-3DR', orbit: 'GEO', altitude: 35786, status: 'active', lastUpdate: '4 min ago' },
]

export const orbitalPredictions = [
  { time: '00:00', pass: 1, elevation: 45 },
  { time: '06:00', pass: 2, elevation: 72 },
  { time: '12:00', pass: 3, elevation: 88 },
  { time: '18:00', pass: 4, elevation: 65 },
]

export const earthWatchAlerts = [
  { id: 1, type: 'vegetation', region: 'Central India', severity: 'medium', message: 'NDVI decline detected' },
  { id: 2, type: 'drought', region: 'Rajasthan', severity: 'high', message: 'Soil moisture below threshold' },
  { id: 3, type: 'flood', region: 'Assam', severity: 'low', message: 'Water extent increased' },
]

export const dashboardStats = {
  activeSatellites: 24,
  alerts: 3,
  missions: 2,
  coverage: 87,
}

export const chandrayaan3Mission = {
  name: 'Chandrayaan-3',
  status: 'Landed',
  phase: 'Surface operations',
  lander: {
    name: 'Vikram',
    status: 'Operational',
    temp: '-40°C',
    power: '98%',
    lastContact: '2 hours ago',
  },
  rover: {
    name: 'Pragyan',
    status: 'Operational',
    distance: '105 m',
    samples: 4,
    lastContact: '1 hour ago',
  },
  telemetry: [
    { label: 'Altitude', value: '0 m', unit: '' },
    { label: 'Latitude', value: '69.37', unit: '°S' },
    { label: 'Longitude', value: '32.32', unit: '°E' },
    { label: 'Temperature', value: '-40', unit: '°C' },
    { label: 'Solar panel', value: '98', unit: '%' },
  ],
  progress: 100,
}

export const earthAnalysisTabs = [
  { id: 'vegetation', label: 'Vegetation', icon: '🌿' },
  { id: 'drought', label: 'Drought', icon: '🏜️' },
  { id: 'urban', label: 'Urban', icon: '🏙️' },
  { id: 'floods', label: 'Floods', icon: '🌊' },
]

export const changeDetectionAlerts = [
  { type: 'vegetation', region: 'Punjab', change: 'Loss', magnitude: '-12%', period: '2016 → 2023' },
  { type: 'drought', region: 'Marathwada', change: 'Drought signal', magnitude: 'High', period: '2016 → 2023' },
  { type: 'urban', region: 'Bengaluru', change: 'Expansion', magnitude: '+28%', period: '2016 → 2023' },
  { type: 'flood', region: 'Bihar', change: 'Flood extent', magnitude: '+15%', period: '2016 → 2023' },
]

export const chartData = [
  { name: 'Jan', value: 72 },
  { name: 'Feb', value: 68 },
  { name: 'Mar', value: 75 },
  { name: 'Apr', value: 80 },
  { name: 'May', value: 78 },
  { name: 'Jun', value: 85 },
  { name: 'Jul', value: 82 },
  { name: 'Aug', value: 88 },
  { name: 'Sep', value: 90 },
  { name: 'Oct', value: 87 },
  { name: 'Nov', value: 84 },
  { name: 'Dec', value: 91 },
]
