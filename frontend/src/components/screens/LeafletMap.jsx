import React, { useEffect, useState } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

export default function LeafletMap({ 
  zone, 
  metricValue, 
  mode, 
  className,
  geoJsonData
}) {
  const [map, setMap] = useState(null)

  // Force map invalidation on load to fix rendering issues
  useEffect(() => {
    if (map) {
      setTimeout(() => {
        map.invalidateSize()
      }, 250)
    }
  }, [map, geoJsonData])

  const getColor = (stateName) => {
    if (!stateName || !zone) return '#1e293b'
    
    // Check if state matches selected zone/district
    if (stateName.toLowerCase().includes(zone.toLowerCase()) || zone.toLowerCase().includes(stateName.toLowerCase())) {
        if (mode === 'vegetation') {
             if (metricValue == null) return '#3b82f6'
             if (metricValue > 0.6) return '#22c55e' // Green
             if (metricValue >= 0.3) return '#eab308' // Yellow
             return '#ef4444' // Red
        } else if (mode === 'drought') {
             if (metricValue == null) return '#3b82f6'
             if (metricValue > 0.7) return '#ef4444' // Severe
             if (metricValue > 0.4) return '#f97316' // Moderate
             if (metricValue > 0.2) return '#eab308' // Mild
             return '#10b981' // None
        }
    }
    return '#1e293b'
  }

  const style = (feature) => {
    return {
      fillColor: getColor(feature.properties.NAME_1),
      weight: 1,
      opacity: 1,
      color: '#334155',
      fillOpacity: 0.8
    }
  }

  return (
    <div className={className} style={{ position: 'relative', zIndex: 0 }}>
      {typeof window !== 'undefined' && (
        <MapContainer 
          center={[22.5937, 78.9629]} 
          zoom={4.5} 
          style={{ height: '100%', width: '100%', background: '#0a0e17', borderRadius: '0.75rem' }}
          ref={setMap}
          zoomControl={false}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
          />
          {geoJsonData && (
            <GeoJSON 
              data={geoJsonData} 
              style={style}
              key={zone + metricValue}
            />
          )}
        </MapContainer>
      )}
    </div>
  )
}
