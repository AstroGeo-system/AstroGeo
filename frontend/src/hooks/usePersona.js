import { usePersonaContext } from '@/context/PersonaContext'

/**
 * Convenience hook — returns everything a component needs to react to persona.
 *
 * Usage:
 *   const { persona, isSimple, translate, visibility } = usePersona()
 */
export function usePersona() {
  const {
    persona,
    personaConfig,
    setPersona,
    clearPersona,
    isSimple,
    setIsSimple,
    toggleSimple,
    translate,
    visibility,
    hydrated,
  } = usePersonaContext()

  return {
    persona,
    personaConfig,
    setPersona,
    clearPersona,
    isSimple,
    setIsSimple,
    toggleSimple,
    translate,
    visibility,
    hydrated,
    isResearcher: persona === 'researcher',
    isFarmer:     persona === 'farmer',
    isStudent:    persona === 'student',
    isJournalist: persona === 'journalist',
    isPolicyMaker: persona === 'policymaker',
  }
}
