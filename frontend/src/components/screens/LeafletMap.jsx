import React, { useEffect, useState } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

export default function LeafletMap({ 
  zone, 
  metricValue, 
  allMetrics,
  mode, 
  className,
  geoJsonData
}) {
  const [map, setMap] = useState(null)

  // Force map invalidation on load to fix rendering issues
  useEffect(() => {
    let timer;
    if (map) {
      timer = setTimeout(() => {
        // Ensure map is still valid and has its container before invalidating
        if (map && typeof map.invalidateSize === 'function') {
            try {
                map.invalidateSize()
            } catch (e) {
                console.warn('Map resize failed during transition:', e)
            }
        }
      }, 500)
    }
    return () => { if (timer) clearTimeout(timer) }
  }, [map, geoJsonData])

  const getColor = (stateName) => {
    if (!stateName) return '#1e293b'
    
    // Check if state has data in allMetrics
    let val = metricValue;
    if (allMetrics) {
      // Find matching key in allMetrics
      const match = Object.keys(allMetrics).find(z => stateName.toLowerCase().includes(z.toLowerCase()) || z.toLowerCase().includes(stateName.toLowerCase()))
      if (match) val = allMetrics[match]
      else val = null
    } else {
      // Fallback to original logic if no allMetrics provided
      if (!(stateName.toLowerCase().includes(zone.toLowerCase()) || zone.toLowerCase().includes(stateName.toLowerCase()))) {
        return '#1e293b'
      }
    }

    if (val == null) return '#1e293b'

    if (mode === 'vegetation') {
         if (val > 0.6) return '#22c55e' // Green
         if (val >= 0.3) return '#eab308' // Yellow
         return '#ef4444' // Red
    } else if (mode === 'drought') {
         if (val > 0.7) return '#ef4444' // Severe
         if (val > 0.4) return '#f97316' // Moderate
         if (val > 0.2) return '#eab308' // Mild
         return '#10b981' // None
    }
    
    return '#1e293b'
  }

  const style = (feature) => {
    const isSelected = feature.properties.NAME_1.toLowerCase().includes(zone.toLowerCase()) || zone.toLowerCase().includes(feature.properties.NAME_1.toLowerCase())
    
    return {
      fillColor: getColor(feature.properties.NAME_1),
      weight: isSelected ? 3 : 1,
      opacity: 1,
      color: isSelected ? '#ffffff' : '#334155',
      fillOpacity: isSelected ? 0.9 : 0.6
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
