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
} from 'lucide-react'
import { cn } from '@/lib/cn'
import { liveStats as staticStats } from '@/data/dashboardData'
import { api } from '@/lib/api'

const nav = [
  { href: '/', label: 'Home', icon: LayoutDashboard },
  { href: '/astronomy', label: 'Astronomy', icon: Telescope },
  { href: '/earth', label: 'Earth', icon: Globe2 },
  { href: '/isro', label: 'ISRO', icon: Rocket },
  { href: '/research', label: 'Research Lab', icon: FlaskConical },
]

export default function DashboardLayout({ children }) {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const [liveStats, setLiveStats] = useState(staticStats)

  useEffect(() => {
    api.getLiveStats().then(([schedule, passes, verified]) => {
      setLiveStats([
        {
          id:    'sat',
          label: 'Active Satellites',
          value: '52',
        },
        {
          id:    'launch',
          label: 'Next ISRO Launch',
          value: schedule?.countdown?.days != null
            ? `${schedule.countdown.days}d`
            : '23d',
        },
        {
          id:    'visible',
          label: 'Visible Tonight',
          value: passes
            ? String(passes.filter(p => (p.maxelevation ?? p.max_el ?? 0) > 30).length)
            : '3',
        },
        {
          id:    'verified',
          label: 'Predictions Verified',
          value: verified?.total
            ? verified.total.toLocaleString()
            : '1,247',
        },
      ])
    })
  }, [])

  const sidebarW = collapsed ? 'w-[72px]' : 'w-[260px]'

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
              <div className="hidden items-center gap-2 text-right sm:block">
                <div className="text-xs text-slate-500">Operator</div>
                <div className="text-sm font-medium text-white">AstroExplorer</div>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-gradient-to-br from-astro-primary/40 to-astro-secondary/30 text-sm font-semibold">
                AE
              </div>
            </div>
          </div>

          {/* Live stats ticker */}
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
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22 }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
