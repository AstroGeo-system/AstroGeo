'use client'

import { useState } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import dynamic from 'next/dynamic'

const GlobeHero = dynamic(
  () => import('@/components/GlobeHero'),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full w-full">
        <div className="text-slate-500 text-sm animate-pulse">Loading globe...</div>
      </div>
    ),
  }
)

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

function GlassCard({ children, className }) {
  return (
    <div className={cn("bg-[#0f172a]/40 backdrop-blur-xl border border-white/10 rounded-2xl", className)}>
      {children}
    </div>
  )
}

function ActionButton({ href, children, variant = 'primary' }) {
  const base = 'inline-flex items-center justify-center px-6 py-2.5 rounded-full text-sm font-medium transition border'
  const styles =
    variant === 'primary'
      ? 'bg-cyan-500/10 border-cyan-400/30 text-cyan-50 shadow-[0_0_15px_rgba(34,211,238,0.2)] hover:bg-cyan-500/20 hover:shadow-[0_0_20px_rgba(34,211,238,0.4)]'
      : 'bg-fuchsia-500/10 border-fuchsia-400/30 text-fuchsia-50 shadow-[0_0_15px_rgba(192,38,211,0.2)] hover:bg-fuchsia-500/20 hover:shadow-[0_0_20px_rgba(192,38,211,0.4)]'
  return (
    <Link href={href} className={`${base} ${styles}`}>
      {children}
    </Link>
  )
}

function FeatureCard({ title, desc, icon, cta, href }) {
  return (
    <div className="bg-[#111827]/60 backdrop-blur-md border border-white/10 rounded-2xl p-4 flex flex-col justify-between hover:bg-[#1a2333]/80 transition-colors group">
      <div>
        <div className="h-10 w-10 rounded-full bg-cyan-900/30 border border-cyan-500/20 flex items-center justify-center text-xl mb-3 group-hover:scale-110 transition-transform shadow-[0_0_15px_rgba(34,211,238,0.15)]">
          {icon}
        </div>
        <div className="font-display font-semibold text-sm tracking-wide text-white uppercase">{title}</div>
        <div className="mt-2 text-xs text-slate-400 leading-relaxed">{desc}</div>
      </div>
      <div className="mt-4">
        <Link href={href} className="inline-flex items-center text-xs font-medium text-cyan-400 hover:text-cyan-300 transition-colors bg-cyan-950/40 px-3 py-1.5 rounded-full border border-cyan-500/20">
          {cta} &rarr;
        </Link>
      </div>
    </div>
  )
}

function AgentUI({ name, id, color }) {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if(!query.trim()) return
    const userMsg = { role: 'user', content: query }
    setMessages(prev => [...prev, userMsg])
    setQuery('')
    setLoading(true)

    try {
      // Connect to the backend provided by the team
      const res = await fetch(`/api/agents/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userMsg.content }),
      })
      if (!res.ok) throw new Error('Network response was not ok')
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'agent', content: data.reply || 'Agent response received.' }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'agent', content: `[Connection error to ${name} backend. Needs team integration.]` }])
    } finally {
      setLoading(false)
    }
  }

  const colorClasses = color === 'orange' ? 'border-orange-500/30 ring-orange-500/20 bg-orange-500/10 text-orange-400' : 'border-blue-500/30 ring-blue-500/20 bg-blue-500/10 text-blue-400'

  return (
    <div className="flex flex-col h-[300px] bg-[#111827]/80 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
      <div className={`p-3 border-b border-white/5 flex items-center gap-2 bg-black/20 text-sm font-semibold tracking-wide ${colorClasses.split(' ').slice(-1)[0]}`}>
        <div className={`w-2 h-2 rounded-full animate-pulse ${color === 'orange' ? 'bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.8)]' : 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]'}`} />
        {name} Terminal
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-xs text-slate-500 text-center mt-10">Awaiting input...</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`text-xs p-2.5 rounded-xl max-w-[85%] ${m.role === 'user' ? 'bg-cyan-900/30 border border-cyan-800/30 text-cyan-50 ml-auto' : 'bg-slate-800/50 border border-slate-700/50 text-slate-200 mr-auto'}`}>
            {m.content}
          </div>
        ))}
        {loading && (
          <div className="text-xs text-slate-500 mr-auto flex gap-1 items-center bg-slate-800/50 p-2.5 rounded-xl border border-slate-700/50">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"/>
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{animationDelay: '0.1s'}}/>
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{animationDelay: '0.2s'}}/>
          </div>
        )}
      </div>
      <form onSubmit={handleSubmit} className="p-3 border-t border-white/5 bg-black/20">
        <div className={`flex items-center bg-black/40 rounded-full border px-3 py-1.5 ${colorClasses.split(' ')[0]} focus-within:ring-2 ${colorClasses.split(' ')[1]}`}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Ask ${name}...`}
            className="flex-1 bg-transparent text-xs text-white outline-none placeholder:text-slate-500"
          />
          <button type="submit" className={`ml-2 text-xs font-medium px-2 py-0.5 rounded cursor-pointer transition ${colorClasses.split(' ').slice(2).join(' ')} hover:brightness-125`}>
            Send
          </button>
        </div>
      </form>
    </div>
  )
}

export default function Home() {
  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10 overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        {/* LEFT globe - Takes up the left half of the screen precisely as in image-4 */}
        <div className="relative h-[550px] w-full flex items-center justify-center">
           {/* Add a radial gradient behind the globe for effect */}
           <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(34,211,238,0.1)_0%,transparent_60%)] pointer-events-none" />
           <GlobeHero />
        </div>

        {/* RIGHT text content */}
        <div>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            <div>
              <h1 className="font-display text-4xl lg:text-5xl font-bold text-white leading-tight uppercase tracking-wide drop-shadow-lg">
                ASTROGEO - AI-POWERED<br/>SPACE INTELLIGENCE
              </h1>
              <p className="mt-4 text-base text-slate-300 font-light tracking-wide">
                Tracking Satellites. Analyzing Earth Changes. Predicting the Future.
              </p>
            </div>

            <div className="flex items-center gap-3 bg-red-950/30 border border-red-500/30 rounded-full py-1.5 px-4 inline-flex shadow-[0_0_15px_rgba(220,38,38,0.15)]">
              <span className="flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
              </span>
              <span className="text-xs font-semibold tracking-wider text-red-500 uppercase">Live Now</span>
              <span className="text-xs text-slate-300 ml-1">ISS Position: Over Indian Ocean. Next Pass: 8:42 PM IST</span>
            </div>

            <div className="flex items-center gap-4 pt-2">
              <ActionButton href="/features" variant="primary">
                Explore Features
              </ActionButton>
              <ActionButton href="/demo" variant="secondary">
                View Demo
              </ActionButton>
            </div>

            {/* Feature Cards Grid (2x2) */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6">
              <FeatureCard
                icon="🌐"
                title="LIVE TRACKING"
                desc="ISS Position, Satellite Passes, Orbital Paths"
                cta="Track Now"
                href="/earth"
              />
              <FeatureCard
                icon="🔮"
                title="PREDICTIONS"
                desc="Asteroid Alerts, Launch Windows, Weather Impact"
                cta="Predict Now"
                href="/research"
              />
              <FeatureCard
                icon="🍃"
                title="EARTH WATCH"
                desc="NDVI Changes, Drought Monitor, Land Cover"
                cta="Analyze Now"
                href="/earth"
              />
              <FeatureCard
                icon="🚀"
                title="ISRO TRACKER"
                desc="Chandrayaan-3, Launch Schedule, Satellite Status"
                cta="Track ISRO"
                href="/isro"
              />
            </div>

            {/* Stats Bar */}
            <div className="mt-8 py-3 border-t border-b border-white/10 flex flex-wrap items-center justify-between text-xs text-slate-400">
              <div className="flex gap-2 items-center">
                <span>Active Satellites:</span> <span className="text-cyan-400 font-semibold">52</span>
              </div>
              <div className="w-px h-4 bg-white/10 hidden sm:block"></div>
              <div className="flex gap-2 items-center">
                <span>Visible Tonight:</span> <span className="text-fuchsia-400 font-semibold">3</span>
              </div>
              <div className="w-px h-4 bg-white/10 hidden sm:block"></div>
              <div className="flex gap-2 items-center">
                <span>Next ISRO Launch:</span> <span className="text-orange-400 font-semibold">23 days</span>
              </div>
              <div className="w-px h-4 bg-white/10 hidden sm:block"></div>
              <div className="flex gap-2 items-center">
                <span>Predictions Verified:</span> <span className="text-green-400 font-semibold">1,247</span>
              </div>
            </div>
            
          </motion.div>
        </div>
      </div>

      {/* Agents & Recent Predictions Section underneath */}
      <div className="mt-16 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Active Agents Integrations (3 columns width each) */}
        <div className="lg:col-span-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <AgentUI name="ISRO Agent" id="isro" color="orange" />
          <AgentUI name="NASA Agent" id="nasa" color="cyan" />
        </div>

        {/* Recent Predictions Feed (6 columns) */}
        <div className="lg:col-span-6">
          <h2 className="font-display font-semibold text-lg text-white mb-4">Recent Predictions Feed</h2>
          <div className="space-y-3">
            {[
              { icon: '☄️', t: 'Asteroid 2024 BX1', s: 'Visible (Verified, 98% Confidence)', color: 'text-green-400' },
              { icon: '☀️', t: 'Drought Detection: Maharashtra', s: 'Analyzing (85% Confidence)', color: 'text-orange-400' },
              { icon: '🛰️', t: 'ISS Pass: 8:42 PM IST', s: 'Upcoming (Max Elevation 60°)', color: 'text-cyan-400' },
            ].map((p, i) => (
              <GlassCard key={i} className="p-4 flex items-center justify-between group cursor-pointer hover:border-white/20 transition-colors">
                <div className="flex items-center gap-3">
                  <div className="text-2xl opacity-80 group-hover:scale-110 transition-transform">{p.icon}</div>
                  <div>
                    <div className="text-sm font-semibold text-white tracking-wide">{p.t}</div>
                    <div className="text-xs text-slate-400 mt-0.5">{p.s}</div>
                  </div>
                </div>
                <div className={`text-xs font-bold ${p.color}`}>LIVE &bull;</div>
              </GlassCard>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
