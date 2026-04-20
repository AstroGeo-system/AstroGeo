'use client'

import { useState, useEffect } from 'react'
import { AnimatePresence } from 'framer-motion'
import { PersonaProvider, usePersonaContext } from '@/context/PersonaContext'
import PersonaSelector from '@/components/onboarding/PersonaSelector'

/**
 * Inner shell — reads persona from context and gates the app behind PersonaSelector.
 * Must be a separate component so it can call usePersonaContext() inside the Provider.
 */
function PersonaGate({ children }) {
  const { persona, setPersona, clearPersona, hydrated } = usePersonaContext()
  const [showSelector, setShowSelector] = useState(false)

  // Once hydrated, decide whether to show selector
  useEffect(() => {
    if (hydrated && !persona) {
      setShowSelector(true)
    }
  }, [hydrated, persona])

  const handleSelect = (id) => {
    setPersona(id)
    setShowSelector(false)
  }

  const handleSwitch = () => {
    clearPersona()
    setShowSelector(true)
  }

  // Expose switch handler globally so DashboardHome banner can trigger it
  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.__astrogeo_switchPersona = handleSwitch
    }
  }, [])

  return (
    <>
      <AnimatePresence>
        {showSelector && (
          <PersonaSelector key="persona-selector" onSelect={handleSelect} />
        )}
      </AnimatePresence>
      {/* Always render children so layout hydrates; PersonaSelector overlays on top */}
      {children}
    </>
  )
}

export default function PersonaShell({ children }) {
  return (
    <PersonaProvider>
      <PersonaGate>{children}</PersonaGate>
    </PersonaProvider>
  )
}
