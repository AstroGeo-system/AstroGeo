# AstroGeo — Space Intelligence Dashboard

A modern, dark-themed space intelligence dashboard frontend built with React, Vite, Tailwind CSS, Three.js, and Recharts.

## Tech Stack

- **React 18** + **Vite 5**
- **Tailwind CSS** — styling and glassmorphism
- **Three.js** (via `@react-three/fiber` + `@react-three/drei`) — 3D Earth and satellite orbits
- **Recharts** — data charts
- **React Router** — navigation

## Design

- Dark futuristic UI with glassmorphism panels
- Blue/cyan glowing accents
- Smooth animations and hover effects
- Responsive layout

## Project Structure

```
src/
  components/
    Navbar.jsx       — Top navigation (Astronomy, Earth, ISRO, Research)
    GlobeViewer.jsx  — Interactive 3D Earth with orbiting satellites
    SatelliteCard.jsx
    PredictionCard.jsx
    EarthTabs.jsx
    MapComparison.jsx
    MissionStatus.jsx
  pages/
    Dashboard.jsx    — Main dashboard with globe, cards, stats, mission panel
    EarthAnalysis.jsx— Earth analysis with tabs, map comparison, change detection
  data/
    placeholderData.js
  styles/
    globals.css
```

## Pages & Features

1. **Main Dashboard** — 3D globe, satellite tracking card, orbital predictions, Earth Watch, active satellites count, stats bar, mission monitoring panel (Chandrayaan-3).
2. **Earth Analysis** — Tabs (Vegetation, Drought, Urban, Floods), 2016 vs 2023 map comparison slider, change detection alerts, mission data chart and mission panel.

## Run Locally

```bash
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

## Build

```bash
npm run build
npm run preview
```

## Notes

- All satellite and mission data is placeholder only (see `src/data/placeholderData.js`).
- Frontend-only; no backend or API calls.
