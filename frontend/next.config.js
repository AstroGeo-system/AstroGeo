const path = require('path')

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  turbopack: {
    resolveAlias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'apod.nasa.gov',
        port: '',
        pathname: '/apod/**',
      },
      {
        protocol: 'https',
        hostname: '*.apod.nasa.gov',
        port: '',
      },
    ],
  },
}

module.exports = nextConfig

