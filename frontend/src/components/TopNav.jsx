'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

const items = [
  { href: '/astronomy', label: 'Astronomy' },
  { href: '/earth', label: 'Earth' },
  { href: '/isro', label: 'ISRO' },
  { href: '/research', label: 'Research' },
]

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

function TopNav() {
  const pathname = usePathname()
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowProfileMenu(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-[#0a0e17]/80 backdrop-blur-md border-b border-white/5">
      <div className="mx-auto max-w-[1400px] px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <span className="text-2xl group-hover:-translate-y-0.5 transition-transform duration-300">🌍</span>
            <span className="font-display text-xl tracking-tight text-white font-bold">
              AstroGeo
            </span>
          </Link>

          {/* Center Links */}
          <nav className="hidden md:flex items-center gap-8">
            {items.map((it) => {
              const active = pathname?.startsWith(it.href)
              return (
                <Link
                  key={it.href}
                  href={it.href}
                  className={`text-sm tracking-wide transition-colors font-medium relative ${
                    active ? 'text-white' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {it.label}
                  {active && (
                    <motion.div layoutId="navIndicator" className="absolute -bottom-6 left-0 right-0 h-0.5 bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.8)]" />
                  )}
                </Link>
              )
            })}
          </nav>

          {/* Right Profile */}
          <div className="flex items-center gap-4 relative" ref={menuRef}>
            
            {/* Notification Bell */}
            <button className="relative p-2 text-slate-400 hover:text-white transition-colors">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
            </button>

            <div 
              className="flex items-center gap-3 hover:bg-white/5 py-1.5 px-3 rounded-full cursor-pointer transition-colors border border-transparent hover:border-slate-800"
              onClick={() => setShowProfileMenu(!showProfileMenu)}
            >
              <img 
                src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=100&q=80" 
                alt="AstroExplorer"
                className="w-8 h-8 rounded-full border-2 border-slate-700"
              />
              <span className="hidden sm:block text-sm text-slate-200 font-semibold tracking-wide">
                AstroExplorer
              </span>
            </div>

            <AnimatePresence>
              {showProfileMenu && (
                <motion.div 
                  initial={{opacity:0, y:10, scale:0.95}} 
                  animate={{opacity:1, y:0, scale:1}} 
                  exit={{opacity:0, y:10, scale:0.95}}
                  className="absolute top-14 right-0 w-64 bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden py-2 z-50 origin-top-right"
                >
                  <div className="px-4 py-3 border-b border-slate-800/80">
                    <div className="text-sm font-bold text-white">AstroExplorer</div>
                    <div className="text-xs text-slate-400">level 12 • Amateur Astronomer</div>
                  </div>
                  
                  <div className="p-2 space-y-1 text-sm text-slate-300">
                    <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-800/80 hover:text-white transition-colors flex items-center gap-3">
                      <span>🔭</span> My Equipment Setup
                    </button>
                    <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-800/80 hover:text-white transition-colors flex items-center gap-3">
                      <span>📸</span> Observation History
                    </button>
                    <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-800/80 hover:text-white transition-colors flex items-center gap-3">
                      <span>⚙️</span> Account Settings
                    </button>
                  </div>
                  
                  <div className="p-2 mt-1 border-t border-slate-800/80">
                    <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-red-500/10 text-slate-400 hover:text-red-400 transition-colors flex items-center gap-3 text-sm">
                      <span>🚪</span> Sign Out
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

          </div>
          
        </div>
      </div>
    </div>
  )
}

export default TopNav
