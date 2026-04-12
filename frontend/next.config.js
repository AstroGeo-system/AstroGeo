/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
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

