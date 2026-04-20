'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { PERSONA_LIST } from '@/data/personaConfig'

export default function PersonaSelector({ onSelect }) {
  const [selected, setSelected] = useState(null)
  const [confirming, setConfirming] = useState(false)

  const handleConfirm = () => {
    if (!selected) return
    setConfirming(true)
    setTimeout(() => {
      onSelect(selected)
    }, 400)
  }

  const handleSkip = () => {
    onSelect('researcher')
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="fixed inset-0 z-[9999] flex flex-col items-center justify-center overflow-y-auto px-4 py-8"
      style={{ background: '#0A0E17' }}
    >
      {/* Background grid overlay */}
      <div className="pointer-events-none absolute inset-0 opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(rgba(59,130,246,0.15) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59,130,246,0.15) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
        }}
      />

      {/* Central glow */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[600px] w-[600px] rounded-full opacity-20"
        style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.4) 0%, transparent 70%)' }}
      />

      <div className="relative z-10 mx-auto w-full max-w-4xl">
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8 flex items-center justify-center gap-3"
        >
          <span className="text-3xl">🚀</span>
          <span className="text-2xl font-bold tracking-tight text-white">AstroGeo</span>
        </motion.div>

        {/* Headline */}
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.18 }}
          className="mb-2 text-center"
        >
          <h1 className="text-4xl font-bold text-white sm:text-5xl">Welcome. Who are you?</h1>
        </motion.div>

        {/* Subheading */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25 }}
          className="mb-10 text-center text-slate-400"
        >
          We'll personalise your experience so the data makes sense to you.
        </motion.p>

        {/* Persona cards — 3 top, 2 bottom */}
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          {PERSONA_LIST.slice(0, 3).map((p, i) => (
            <PersonaCard
              key={p.id}
              persona={p}
              selected={selected === p.id}
              index={i}
              onSelect={setSelected}
            />
          ))}
        </div>
        <div className="mb-10 grid gap-4 sm:grid-cols-2 sm:px-[16.66%]">
          {PERSONA_LIST.slice(3).map((p, i) => (
            <PersonaCard
              key={p.id}
              persona={p}
              selected={selected === p.id}
              index={3 + i}
              onSelect={setSelected}
            />
          ))}
        </div>

        {/* Confirm button */}
        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          onClick={handleConfirm}
          disabled={!selected || confirming}
          className={`
            mx-auto block w-full max-w-sm rounded-xl py-4 text-base font-semibold transition-all duration-300
            ${selected
              ? 'bg-white text-black shadow-[0_0_32px_rgba(255,255,255,0.2)] hover:bg-slate-100'
              : 'cursor-not-allowed bg-slate-800 text-slate-500'}
          `}
        >
          {confirming
            ? 'Loading your experience…'
            : selected
            ? `Continue as ${PERSONA_LIST.find(p => p.id === selected)?.emoji} ${PERSONA_LIST.find(p => p.id === selected)?.label} →`
            : 'Select a persona to continue'}
        </motion.button>

        {/* Skip link */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-4 text-center"
        >
          <button
            onClick={handleSkip}
            className="text-sm text-slate-500 underline-offset-2 hover:text-slate-400 hover:underline"
          >
            Skip — show me everything
          </button>
        </motion.p>
      </div>
    </motion.div>
  )
}

function PersonaCard({ persona, selected, index, onSelect }) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 + index * 0.07 }}
      onClick={() => onSelect(persona.id)}
      className={`
        relative rounded-2xl border p-6 text-left transition-all duration-300 outline-none
        ${selected
          ? `${persona.borderClass} ${persona.bgClass} ${persona.glowClass}`
          : 'border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.06]'}
      `}
    >
      {/* Selected checkmark */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            className={`absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full border text-xs font-bold text-white ${persona.borderClass}`}
            style={{ background: persona.color }}
          >
            ✓
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mb-3 text-3xl">{persona.emoji}</div>
      <div className="mb-0.5 text-base font-semibold text-white">{persona.label}</div>
      <div className={`mb-3 text-xs font-medium ${persona.colorClass}`}>{persona.subtitle}</div>
      <p className="text-sm leading-relaxed text-slate-400">{persona.description}</p>
    </motion.button>
  )
}
