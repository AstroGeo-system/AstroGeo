'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { PERSONAS, getVisibility, translate as translateTerm } from '@/data/personaConfig'

const STORAGE_KEY = 'astrogeo_persona'

const PersonaContext = createContext(null)

export function PersonaProvider({ children }) {
  const [persona, setPersonaState]   = useState(null)   // null = not yet selected
  const [isSimple, setIsSimple]       = useState(true)   // plain English toggle
  const [hydrated, setHydrated]       = useState(false)  // SSR guard

  // Read from localStorage on mount (client only)
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored && PERSONAS[stored]) {
        setPersonaState(stored)
      }
    } catch (_) {}
    setHydrated(true)
  }, [])

  const setPersona = useCallback((id) => {
    setPersonaState(id)
    try {
      if (id) {
        localStorage.setItem(STORAGE_KEY, id)
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    } catch (_) {}
  }, [])

  const clearPersona = useCallback(() => {
    setPersonaState(null)
    try { localStorage.removeItem(STORAGE_KEY) } catch (_) {}
  }, [])

  const toggleSimple = useCallback(() => setIsSimple(v => !v), [])

  const translate = useCallback((key, value) => {
    if (!isSimple || persona === 'researcher') return value
    return translateTerm(key, value)
  }, [isSimple, persona])

  const visibility = getVisibility(persona ?? 'researcher')

  const value = {
    persona,            // string | null
    personaConfig: persona ? PERSONAS[persona] : null,
    setPersona,
    clearPersona,
    isSimple,
    setIsSimple,
    toggleSimple,
    translate,
    visibility,
    hydrated,
  }

  return (
    <PersonaContext.Provider value={value}>
      {children}
    </PersonaContext.Provider>
  )
}

export function usePersonaContext() {
  const ctx = useContext(PersonaContext)
  if (!ctx) throw new Error('usePersonaContext must be used inside <PersonaProvider>')
  return ctx
}
