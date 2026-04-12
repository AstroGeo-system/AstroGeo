'use client'

import { useEffect, useState, useRef } from 'react';
import dynamic from 'next/dynamic';
const Globe = dynamic(() => import('react-globe.gl'), { ssr: false });

function getColor(name = '') {
  if (name.includes('ISS')) return 'red';
  if (name.includes('STARLINK')) return '#00aaff';
  if (name.includes('GPS') || name.includes('GALILEO')) return 'yellow';
  return '#00ffff';
}

function getSize() {
  return 0.12;
}

function generateOrbitPath(sat) {
  const points = [];
  for (let i = 0; i < 360; i += 3) {
    const angle = i * (Math.PI / 180);
    const radius = 10;
    points.push({
      lat: Math.sin(angle) * radius,
      lng: Math.cos(angle) * radius + sat.lng
    });
  }
  return points;
}

const SatelliteGlobe = ({ height = '100%', className = '' }) => {
  const [orbits, setOrbits] = useState([]);
  const [selectedSat, setSelectedSat] = useState(null);
  const [satellites, setSatellites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [globeReady, setGlobeReady] = useState(false);
  const [hoveredSatellite, setHoveredSatellite] = useState(null);
  const [lightMode, setLightMode] = useState(false);

  const globeRef = useRef();

  const getElevation = (sat) => {
    if (!sat) return 0;
    if (hoveredSatellite && hoveredSatellite.id === sat.id) {
      return 0.2;
    }
    return 0.05;
  };

  const handleSatelliteHover = (sat) => {
    setHoveredSatellite(sat);
  };

  const fetchSatellites = async () => {
    try {
      const response = await fetch('http://localhost:3001/satellites');
      const data = await response.json();

      const satArray = data.satellites || data.above || [];

      const processed = satArray.map((sat, i) => ({
        id: i,
        name: sat.name || sat.satname,
        lat: sat.lat || sat.satlat,
        lng: sat.lng || sat.satlng,
        altitude: sat.altitude || 0.2,
        altitudeKm: sat.altitudeKm || sat.satalt,
        color: getColor(sat.name || sat.satname || ''),
        size: getSize(),
        label: `${sat.name || sat.satname}\nAltitude: ${(sat.altitudeKm || sat.satalt || 0).toFixed(2)} km`
      }));

      setSatellites(processed);

      const orbitData = processed
        .slice(0, 20)
        .map(sat => ({
          points: generateOrbitPath(sat),
          color: '#00ffff'
        }));

      setOrbits(orbitData);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSatellites();

    const interval = setInterval(() => {
      fetchSatellites();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (globeRef.current && globeReady) {
      const globe = globeRef.current;
      globe.pointOfView({ lat: 20, lng: 0, altitude: 2.5 }, 1000);
      globe.controls().autoRotate = true;
      globe.controls().autoRotateSpeed = 0.3;
    }
  }, [globeReady]);

  useEffect(() => {
    if (!selectedSat) return;

    const sat = satellites.find(s => s.name === selectedSat.name);
    if (!sat) return;

    globeRef.current?.pointOfView({
      lat: sat.lat,
      lng: sat.lng,
      altitude: 1.5
    }, 500);
  }, [satellites, selectedSat]);

  const handleGlobeReady = () => {
    setGlobeReady(true);
  };

  const toggleLightMode = () => {
    setLightMode(!lightMode);
  };

  const handleClick = (sat) => {
    setSelectedSat(sat);

    if (globeRef.current) {
      globeRef.current.pointOfView({
        lat: sat.lat,
        lng: sat.lng,
        altitude: 1.5
      }, 1000);
    }
  };

  const globeConfig = lightMode ? {
    globeImageUrl: "//unpkg.com/three-globe/example/img/earth-day.jpg",
    backgroundColor: '#87ceeb'
  } : {
    globeImageUrl: "//unpkg.com/three-globe/example/img/earth-blue-marble.jpg",
    backgroundImageUrl: "//unpkg.com/three-globe/example/img/night-sky.png",
    backgroundColor: '#000011'
  };

  return (
    <div className="w-full h-full rounded-xl overflow-hidden ${className}" style={{ height }}>
      <Globe
        globeContainerProps={{
          style: { transform: 'translate(-8%, -8%) scale(0.85)' }
        }}
        ref={globeRef}
        className="w-full h-full"
        globeImageUrl={globeConfig.globeImageUrl}
        backgroundImageUrl={globeConfig.backgroundImageUrl}
        backgroundColor={globeConfig.backgroundColor}
        atmosphereColor="#00aaff"
        atmosphereAltitude={0.15}
        pointsData={satellites}
        pointLat="lat"
        pointLng="lng"
        pointAltitude={(d) => getElevation(d)}
        pointRadius={(d) => d.size}
        pointColor={(d) => d.color}
        pointLabel={(d) => d.label}
        pathsData={orbits}
        pathPoints="points"
        pathColor={() => '#00ffff'}
        pathWidth={0.5}
        pathDashLength={0.5}
        pathDashGap={0.2}
        pathDashAnimateTime={2000}
        onPointClick={handleClick}
        onPointHover={handleSatelliteHover}
        onGlobeReady={handleGlobeReady}
      />
      {/* Controls */}
      <button
        onClick={toggleLightMode}
        className="absolute top-4 left-4 z-50 p-2.5 rounded-full border-none cursor-pointer bg-black/60 backdrop-blur-md text-white hover:bg-black/80 transition-all text-xs font-bold shadow-2xl"
        title="Toggle theme"
      >
        {lightMode ? '🌙' : '☀️'}
      </button>

      {/* Stats */}
      <div className="absolute bottom-3 left-3 bg-black/60 backdrop-blur-md text-white px-3 py-1.5 rounded-full text-xs font-mono tracking-tight z-50 shadow-2xl">
        🛰️ {satellites.length.toLocaleString()}
      </div>

      {/* Selection Panel */}
      {selectedSat && (
        <div className="absolute top-4 right-4 w-80 max-h-[70vh] overflow-hidden bg-gradient-to-b from-black/95 to-black/70 backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl z-50">
          <div className="p-5 border-b border-white/10">
            <h3 className="font-bold text-lg flex items-center gap-2 text-orange-400 mb-1">📡 {selectedSat.name}</h3>
            <button 
              onClick={() => setSelectedSat(null)}
              className="ml-auto text-white/70 hover:text-white text-sm font-medium flex items-center gap-1 transition-colors"
            >
              × Close
            </button>
          </div>
          <div className="p-5 max-h-[calc(70vh-80px)] overflow-y-auto space-y-3 text-sm">
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="space-y-1">
                <span className="text-white/60 text-xs uppercase tracking-wider font-mono">Altitude</span>
                <span className="font-bold text-cyan-400">{selectedSat.altitudeKm?.toFixed(0)}km</span>
              </div>
              <div className="space-y-1">
                <span className="text-white/60 text-xs uppercase tracking-wider font-mono">Position</span>
                <span className="font-mono">{selectedSat.lat.toFixed(1)}°, {selectedSat.lng.toFixed(1)}°</span>
              </div>
            </div>
            <div className="pt-2 pb-4 border-t border-white/10">
              <div className="text-xs text-white/70 mb-2 font-mono uppercase tracking-wider">Label</div>
              <div className="text-white/90 font-mono whitespace-pre-wrap text-xs leading-tight">{selectedSat.label}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SatelliteGlobe;

