'use client'

import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const AppShellContext = createContext(null)

function safeJsonParse(value, fallback) {
  try {
    return JSON.parse(value)
  } catch {
    return fallback
  }
}

const HOME_CITY_KEY = 'astrogeo.homeCity'
const DEFAULT_HOME_CITY = 'Mumbai, MH'

export function AppShellProvider({ children }) {
  const [theme, setTheme] = useState('dark') // 'dark' | 'light'
  const [user, setUser] = useState(null) // { name: string } | null
  const [homeCity, setHomeCityState] = useState(DEFAULT_HOME_CITY)

  useEffect(() => {
    const storedTheme =
      typeof window !== 'undefined' ? localStorage.getItem('astrogeo.theme') : null
    const storedUser =
      typeof window !== 'undefined' ? localStorage.getItem('astrogeo.user') : null
    const storedCity =
      typeof window !== 'undefined' ? localStorage.getItem(HOME_CITY_KEY) : null

    const t = storedTheme === 'light' ? 'light' : 'dark'
    setTheme(t)
    setUser(storedUser ? safeJsonParse(storedUser, null) : null)
    if (storedCity && typeof storedCity === 'string') setHomeCityState(storedCity)
  }, [])

  useEffect(() => {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    if (theme === 'dark') root.classList.add('dark')
    else root.classList.remove('dark')
    try {
      localStorage.setItem('astrogeo.theme', theme)
    } catch {}
  }, [theme])

  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      if (user) localStorage.setItem('astrogeo.user', JSON.stringify(user))
      else localStorage.removeItem('astrogeo.user')
    } catch {}
  }, [user])

  const setHomeCity = useMemo(
    () => (city) => {
      setHomeCityState(city)
      if (typeof window === 'undefined') return
      try {
        localStorage.setItem(HOME_CITY_KEY, city)
      } catch {}
    },
    []
  )

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      user,
      setUser,
      loginDemo: () => setUser({ name: 'AstroExplorer' }),
      logout: () => setUser(null),
      homeCity,
      setHomeCity,
    }),
    [theme, user, homeCity, setHomeCity]
  )

  return <AppShellContext.Provider value={value}>{children}</AppShellContext.Provider>
}

export function useAppShell() {
  const ctx = useContext(AppShellContext)
  if (!ctx) throw new Error('useAppShell must be used within AppShellProvider')
  return ctx
}

