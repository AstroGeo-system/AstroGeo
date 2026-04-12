'use client'

import { useEffect, useRef } from "react"

export default function GlobeViewer() {
  const globeRef = useRef(null)

  useEffect(() => {
    let globe

    const initGlobe = async () => {
      const og = await import("@openglobus/og")

      globe = new og.Globe({
        target: globeRef.current,
      })

      const osmLayer = new og.layer.XYZ({
        url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        isBaseLayer: true,
      })

      globe.planet.addLayer(osmLayer)

      globe.planet.camera.setLonLat(
        new og.LonLat(78.9629, 20.5937, 20000000)
      )
    }

    initGlobe()

    return () => {
      if (globe) globe.destroy()
    }
  }, [])

  return (
    <div className="w-full h-full min-h-[400px] rounded-xl overflow-hidden bg-space-800/50 border border-white/10">
      <div ref={globeRef} className="w-full h-full" />
    </div>
  )
}