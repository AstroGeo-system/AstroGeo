const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');

const app = express();
app.use(cors());

const satellite = require('satellite.js');

app.get('/satellites', async (req, res) => {
    try {
        const response = await fetch(
            'https://api.n2yo.com/rest/v1/satellite/above/0/0/0/90/0/&apiKey=your api key '
        );

        const data = await response.json();
        console.log("API RESPONSE:", data);

        const satArray = data.above || [];

const satellites = satArray
  .slice(0, 150) // ✅ LIMIT (IMPORTANT)
  .map((sat, i) => ({
    id: i,
    name: sat.satname,
    lat: sat.satlat,
    lng: sat.satlng,
    altitude: 0.2,
    altitudeKm: sat.satalt
}));

let cachedData = null;
let lastFetchTime = 0;

        res.json({ satellites });

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
    }
});

const PORT = 3001;
const server = app.listen(PORT, () => {
    console.log(`🚀 USGS Earthquake Proxy server running on http://localhost:${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('ℹ️ SIGTERM received. Shutting down gracefully...');
    server.close(() => {
        console.log('ℹ️ Server closed');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    console.log('ℹ️ SIGINT received. Shutting down gracefully...');
    server.close(() => {
        console.log('ℹ️ Server closed');
        process.exit(0);
    });
}); 
