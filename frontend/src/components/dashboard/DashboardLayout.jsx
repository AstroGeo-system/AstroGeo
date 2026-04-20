'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Telescope,
  Globe2,
  Rocket,
  FlaskConical,
  PanelLeftClose,
  PanelLeft,
  Activity,
  Radio,
  ShieldCheck,
} from 'lucide-react'
import { cn } from '@/lib/cn'
import { liveStats as staticStats } from '@/data/dashboardData'
import { api } from '@/lib/api'
import PlainEnglishToggle from '@/components/persona/PlainEnglishToggle'
import { usePersona } from '@/hooks/usePersona'

const nav = [
  { href: '/', label: 'Home', icon: LayoutDashboard },
  { href: '/astronomy', label: 'Astronomy', icon: Telescope },
  { href: '/earth', label: 'Earth', icon: Globe2 },
  { href: '/isro', label: 'ISRO', icon: Rocket },
  { href: '/research', label: 'Research Lab', icon: FlaskConical },
]

// ── U5: Build persona-aware ticker items ─────────────────────────
function buildPersonaTicker(persona, liveData) {
  const { schedule, passes, verified, drought, solar } = liveData

  const launchDays = schedule?.countdown?.days != null
    ? `${schedule.countdown.days}d`
    : '23d'

  const passArray = Array.isArray(passes) ? passes :
    Array.isArray(passes?.passes) ? passes.passes : []
  const visibleCount = String(passArray.filter(p => (p.maxelevation ?? p.max_el ?? 0) > 30).length || 3)

  const verifiedCount = verified?.total
    ? verified.total.toLocaleString()
    : '1,247'

  const droughtAlerts = drought ?? '2'

  const eventsArray = Array.isArray(solar?.events) ? solar.events :
    Array.isArray(solar?.data) ? solar.data :
    Array.isArray(solar) ? solar : []
  const solarStatus = eventsArray.some(e => e.classType?.startsWith('X') || e.classType?.startsWith('M'))
    ? 'ACTIVE' : 'CALM'

  switch (persona) {
    case 'farmer':
      return [
        { id: 'drought', label: 'Drought Alerts',  value: droughtAlerts },
        { id: 'zones',   label: 'Zones Monitored', value: '17' },
        { id: 'solar',   label: 'Solar Risk',       value: solarStatus },
        { id: 'launch',  label: 'Next ISRO Launch', value: launchDays },
      ]
    case 'student':
      return [
        { id: 'visible',   label: 'Visible Tonight',   value: visibleCount },
        { id: 'asteroids', label: 'Asteroids Tracked',  value: '5,836' },
        { id: 'sat',       label: 'Active Satellites',  value: '52' },
        { id: 'launch',    label: 'Next ISRO Launch',   value: launchDays },
      ]
    case 'journalist':
      return [
        { id: 'solar',     label: 'Solar Activity',    value: solarStatus },
        { id: 'drought',   label: 'Drought Zones',     value: droughtAlerts },
        { id: 'asteroids', label: 'Asteroid Alerts',   value: '3' },
        { id: 'launch',    label: 'ISRO Launch in',    value: launchDays },
      ]
    case 'policymaker':
      return [
        { id: 'high-risk', label: 'High-Risk Districts', value: droughtAlerts },
        { id: 'zones',     label: 'Zones Monitored',     value: '17' },
        { id: 'isro-rate', label: 'ISRO Success Rate',   value: '86%' },
        { id: 'solar',     label: 'Solar Status',        value: solarStatus },
      ]
    default: // researcher + fallback
      return [
        { id: 'verified', label: 'Predictions Verified', value: verifiedCount },
        { id: 'sat',      label: 'Active Satellites',     value: '52' },
        { id: 'visible',  label: 'Visible Tonight',       value: visibleCount },
        { id: 'launch',   label: 'Next ISRO Launch',      value: launchDays },
      ]
  }
}

export default function DashboardLayout({ children }) {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  // Raw live data
  const [rawData, setRawData] = useState({
    schedule: null, passes: null, verified: null, drought: null, solar: null
  })

  const { persona, isResearcher, clearPersona } = usePersona()

  useEffect(() => {
    api.getLiveStats().then(([schedule, passes, verified]) => {
      setRawData(prev => ({ ...prev, schedule, passes, verified }))
    })
    // Fetch drought count for farmer/policymaker ticker
    api.getDrought('Maharashtra').then(d => {
      const count = d?.severity === 'Severe' ? '4' : d?.severity === 'Moderate' ? '2' : '1'
      setRawData(prev => ({ ...prev, drought: count }))
    }).catch(() => {})
    // Fetch solar events for journalist/policymaker/farmer ticker
    api.getSolarEvents().then(s => {
      setRawData(prev => ({ ...prev, solar: s }))
    }).catch(() => {})
  }, [])

  const liveStats = buildPersonaTicker(persona, rawData)
  const sidebarW = collapsed ? 'w-[72px]' : 'w-[260px]'

  // U7: handler for researcher Full Access chip → opens selector
  const handleSwitchPersona = () => {
    clearPersona()
  }

  return (
    <div className="relative z-10 min-h-screen text-slate-100">
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen border-r border-white/10 bg-[#0A0A0A]/90 backdrop-blur-xl transition-[width] duration-300',
          sidebarW
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-white/10 px-3">
          {!collapsed && (
            <Link href="/" className="flex items-center gap-2 px-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-astro-primary/30 text-astro-secondary">
                <Rocket className="h-4 w-4" />
              </span>
              <span className="font-semibold tracking-tight text-white">AstroGeo</span>
            </Link>
          )}
          {collapsed && (
            <Link href="/" className="mx-auto flex h-8 w-8 items-center justify-center rounded-lg bg-astro-primary/30">
              <Rocket className="h-4 w-4 text-astro-secondary" />
            </Link>
          )}
        </div>
        <nav className="space-y-1 p-2 pt-4">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== '/' && pathname?.startsWith(href))
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  active
                    ? 'bg-astro-primary/25 text-white border border-astro-primary/40'
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                )}
                title={collapsed ? label : undefined}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{label}</span>}
              </Link>
            )
          })}
        </nav>
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="absolute bottom-4 left-1/2 flex h-9 w-9 -translate-x-1/2 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </aside>

      <div
        className={cn(
          'min-h-screen transition-[padding] duration-300',
          collapsed ? 'pl-[72px]' : 'pl-[260px]'
        )}
      >
        <header className="sticky top-0 z-30 border-b border-white/10 bg-[#0A0A0A]/80 backdrop-blur-md">
          <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-4 py-3 lg:px-8">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <div className="hidden items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300 sm:flex">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                </span>
                LIVE
              </div>
              <div className="min-w-0 flex-1 overflow-hidden rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <Radio className="h-3.5 w-3.5 shrink-0 text-astro-secondary" />
                  <span className="truncate font-mono-ui text-slate-300">
                    Status stream · All systems nominal · Uplink 99.2%
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <PlainEnglishToggle />

              {/* U7: Full Access chip — only visible for Researcher persona */}
              {isResearcher && (
                <button
                  id="researcher-full-access-chip"
                  onClick={handleSwitchPersona}
                  title="You are in Researcher mode — all data, models, and evidence chains are visible. Other personas see a simplified view. Click to switch persona."
                  className="hidden items-center gap-1.5 rounded-lg border border-blue-500/40 px-3 py-1.5 text-xs font-medium text-blue-400 transition hover:bg-blue-500/10 sm:flex"
                >
                  <ShieldCheck className="h-3 w-3" />
                  Full Access
                </button>
              )}

              <div className="hidden items-center gap-2 text-right sm:block">
                <div className="text-xs text-slate-500">Operator</div>
                <div className="text-sm font-medium text-white">AstroExplorer</div>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-gradient-to-br from-astro-primary/40 to-astro-secondary/30 text-sm font-semibold">
                AE
              </div>
            </div>
          </div>

          {/* U5: Persona-aware live stats ticker */}
          <div className="border-t border-white/5 bg-[#050508]/80">
            <div className="relative mx-auto max-w-[1400px] overflow-hidden py-2">
              <div className="flex animate-ticker whitespace-nowrap will-change-transform">
                {[...liveStats, ...liveStats].map((s, i) => (
                  <span
                    key={`${s.id}-${i}`}
                    className="inline-flex items-center gap-2 px-8 text-xs text-slate-400"
                  >
                    <Activity className="h-3.5 w-3.5 text-astro-secondary" />
                    <span className="text-slate-500">{s.label}:</span>
                    <span className="font-mono-ui font-semibold text-white">{s.value}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-[1400px] px-4 py-8 lg:px-8">
          <div key={pathname}>
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
