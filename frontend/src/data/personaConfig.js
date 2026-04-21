export const PERSONAS = {
  researcher: {
    id: 'researcher',
    label: 'Researcher',
    emoji: '🧪',
    subtitle: 'Deep technical view',
    description: 'See full metrics, model details, and evidence chains.',
  },
  founder: {
    id: 'founder',
    label: 'Founder',
    emoji: '📈',
    subtitle: 'Business-focused summary',
    description: 'Prioritize outcomes, risks, and clear decisions.',
  },
  student: {
    id: 'student',
    label: 'Student',
    emoji: '🎓',
    subtitle: 'Learn by exploration',
    description: 'Guided explanations with practical examples.',
  },
  farmer: {
    id: 'farmer',
    label: 'Farmer',
    emoji: '🌾',
    subtitle: 'Field-level signals',
    description: 'Simple crop/weather impact with actionable alerts.',
  },
  operator: {
    id: 'operator',
    label: 'Mission Operator',
    emoji: '🛰️',
    subtitle: 'Operational monitoring',
    description: 'Fast status updates, anomalies, and launch-readiness cues.',
  },
}

export const PERSONA_LIST = [
  {
    ...PERSONAS.researcher,
    color: '#22d3ee',
    colorClass: 'text-cyan-300',
    borderClass: 'border-cyan-500/50',
    bgClass: 'bg-cyan-500/10',
    glowClass: 'shadow-[0_0_30px_rgba(34,211,238,0.2)]',
  },
  {
    ...PERSONAS.founder,
    color: '#a78bfa',
    colorClass: 'text-violet-300',
    borderClass: 'border-violet-500/50',
    bgClass: 'bg-violet-500/10',
    glowClass: 'shadow-[0_0_30px_rgba(167,139,250,0.2)]',
  },
  {
    ...PERSONAS.student,
    color: '#60a5fa',
    colorClass: 'text-blue-300',
    borderClass: 'border-blue-500/50',
    bgClass: 'bg-blue-500/10',
    glowClass: 'shadow-[0_0_30px_rgba(96,165,250,0.2)]',
  },
  {
    ...PERSONAS.farmer,
    color: '#34d399',
    colorClass: 'text-emerald-300',
    borderClass: 'border-emerald-500/50',
    bgClass: 'bg-emerald-500/10',
    glowClass: 'shadow-[0_0_30px_rgba(52,211,153,0.2)]',
  },
  {
    ...PERSONAS.operator,
    color: '#f59e0b',
    colorClass: 'text-amber-300',
    borderClass: 'border-amber-500/50',
    bgClass: 'bg-amber-500/10',
    glowClass: 'shadow-[0_0_30px_rgba(245,158,11,0.2)]',
  },
]

export function getVisibility(personaId = 'researcher') {
  const base = {
    showModelDetails: true,
    showEvidenceChain: true,
    showAdvancedCharts: true,
    showModelCards: true,
    showAuditLog: true,
  }

  if (personaId === 'founder') {
    return { ...base, showAdvancedCharts: false, showModelCards: false }
  }
  if (personaId === 'student') {
    return { ...base, showModelDetails: false, showModelCards: false, showAuditLog: false }
  }
  if (personaId === 'farmer') {
    return { ...base, showModelDetails: false, showAdvancedCharts: false, showModelCards: false, showAuditLog: false }
  }
  return base
}

const TERM_MAP = {
  anomaly: 'unusual event',
  anomalies: 'unusual events',
  ndvi: 'vegetation health index',
  precipitation: 'rainfall',
  confidence: 'certainty',
  probability: 'chance',
}

export function translate(_key, value) {
  if (typeof value !== 'string') return value
  let out = value
  for (const [from, to] of Object.entries(TERM_MAP)) {
    out = out.replace(new RegExp(`\\b${from}\\b`, 'gi'), to)
  }
  return out
}

