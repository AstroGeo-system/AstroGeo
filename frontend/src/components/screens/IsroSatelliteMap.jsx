import React, { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

// Create a custom glassmorphic icon for satellites
const createSatelliteIcon = (color) => L.divIcon({
  className: 'custom-sat-icon',
  html: `<div style="
    width: 20px; 
    height: 20px; 
    border-radius: 50%; 
    background: ${color}40; 
    border: 2px solid ${color};
    box-shadow: 0 0 10px ${color}80;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    transform: translate(-50%, -50%);
  ">
    <div style="width: 6px; height: 6px; background: #fff; border-radius: 50%;"></div>
  </div>`,
  iconSize: [20, 20],
  iconAnchor: [0, 0],
})

const getSatColor = (health) => {
  if (health > 90) return '#10b981' // emerald-500
  if (health > 70) return '#f59e0b' // amber-500
  return '#ef4444' // red-500
}

export default function IsroSatelliteMap({ fleetData, className }) {
  const [map, setMap] = useState(null)

  // Force map invalidation on load to fix rendering issues
  useEffect(() => {
    let timer;
    if (map) {
      timer = setTimeout(() => {
        if (map && typeof map.invalidateSize === 'function') {
            try { map.invalidateSize() } catch (e) {}
        }
      }, 500)
    }
    return () => { if (timer) clearTimeout(timer) }
  }, [map])

  // Optional: Center map on bounding box of satellites if desired, but 
  // keeping it centered on India/World is usually better for overview.

  return (
    <div className={className} style={{ position: 'relative', zIndex: 0 }}>
      {typeof window !== 'undefined' && (
        <MapContainer 
          center={[20.5937, 78.9629]} // Center on India
          zoom={2.5} 
          style={{ height: '100%', width: '100%', background: '#0a0e17', borderRadius: '0.75rem' }}
          ref={setMap}
          zoomControl={true}
          worldCopyJump={true}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          />
          
          {fleetData?.map((sat) => (
            <Marker 
              key={sat.id} 
              position={[sat.latitude, sat.longitude]}
              icon={createSatelliteIcon(getSatColor(sat.health))}
            >
              <Popup className="sat-popup">
                <div style={{ background: '#1e293b', padding: '8px', borderRadius: '8px', color: '#f8fafc', border: '1px solid #334155', minWidth: '150px' }}>
                  <h4 style={{ margin: 0, fontWeight: 'bold', fontSize: '14px', borderBottom: '1px solid #334155', paddingBottom: '4px', marginBottom: '8px' }}>
                    {sat.name}
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '11px', color: '#94a3b8' }}>
                    <span>Altitude:</span> <span style={{ color: '#fff' }}>{Math.round(sat.altitude_km)} km</span>
                    <span>Lat/Lon:</span> <span style={{ color: '#fff' }}>{sat.latitude.toFixed(2)}°, {sat.longitude.toFixed(2)}°</span>
                    <span>Status:</span> <span style={{ color: sat.eclipsed ? '#94a3b8' : '#eab308' }}>{sat.eclipsed ? 'Eclipsed' : 'Sunlit'}</span>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      )}
    </div>
  )
}
