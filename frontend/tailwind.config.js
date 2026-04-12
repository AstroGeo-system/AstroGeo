/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}",
    "./src/pages/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        astro: {
          bg: '#0A0A0A',
          primary: '#0B3D91',
          secondary: '#FF6B35',
        },
        space: {
          900: '#0a0e17',
          800: '#0f1629',
          700: '#151d33',
          600: '#1a2540',
          500: '#243352',
        },
        accent: {
          cyan: '#00d4ff',
          blue: '#3b82f6',
          glow: 'rgba(0, 212, 255, 0.4)',
        },
      },
      fontFamily: {
        display: ['Inter', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'glow': '0 0 20px rgba(0, 212, 255, 0.3)',
        'glow-lg': '0 0 40px rgba(0, 212, 255, 0.2)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.3)',
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
        'stars': 'stars-shift 120s linear infinite',
        'ticker': 'ticker 28s linear infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(0, 212, 255, 0.3)' },
          '50%': { boxShadow: '0 0 30px rgba(0, 212, 255, 0.5)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'stars-shift': {
          '0%': { transform: 'translate3d(0,0,0)' },
          '100%': { transform: 'translate3d(-80px,-40px,0)' },
        },
        'ticker': {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
      },
    },
  },
  plugins: [],
}
