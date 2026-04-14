'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const SUGGESTION_CHIPS = [
  { label: 'What asteroids are at risk today?', icon: '☄️' },
  { label: 'Did the May 2024 storm affect Maharashtra?', icon: '⛈️' },
  { label: 'What is today\'s launch probability?', icon: '🚀' },
  { label: 'Which vegetation zones show the most decline?', icon: '🌿' },
]

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2 bg-slate-800/60 rounded-2xl rounded-tl-sm w-fit">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  )
}

export default function ChatWidget() {
  const [isOpen, setIsOpen]         = useState(false)
  const [isOnline, setIsOnline]     = useState(true)
  const [messages, setMessages]     = useState([])
  const [input, setInput]           = useState('')
  const [loading, setLoading]       = useState(false)
  const messagesEndRef               = useRef(null)
  const inputRef                     = useRef(null)

  // Check if backend /api/chat is reachable
  useEffect(() => {
    fetch(`${BASE}/health`, { method: 'GET' })
      .then((r) => setIsOnline(r.ok))
      .catch(() => setIsOnline(false))
  }, [])

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 300)
  }, [isOpen])

  const sendMessage = async (text) => {
    const userQuery = (text ?? input).trim()
    if (!userQuery || loading) return

    const userMsg = { role: 'user', content: userQuery }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${BASE}/api/chat`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          messages:   newMessages,
          user_query: userQuery,
        }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const assistantMsg = { role: 'assistant', content: data.reply }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            "I tried to fetch the latest data but encountered an error. Please try again in a moment.",
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <>
      {/* Floating trigger button */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
        <AnimatePresence>
          {!isOpen && !isOnline && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="text-xs text-slate-400 bg-slate-900 border border-slate-700 rounded-full px-3 py-1 shadow"
            >
              Chatbot offline
            </motion.div>
          )}
        </AnimatePresence>

        <motion.button
          id="chat-widget-trigger"
          whileHover={{ scale: isOnline ? 1.08 : 1 }}
          whileTap={{ scale: isOnline ? 0.95 : 1 }}
          onClick={() => isOnline && setIsOpen((v) => !v)}
          className={`
            w-14 h-14 rounded-full flex items-center justify-center shadow-2xl transition-all duration-200
            ${isOnline
              ? 'bg-gradient-to-br from-cyan-500 to-indigo-600 cursor-pointer shadow-[0_0_24px_rgba(34,211,238,0.5)]'
              : 'bg-slate-700 cursor-not-allowed opacity-60'
            }
            ${isOnline && !isOpen ? 'animate-[pulse_3s_ease-in-out_infinite]' : ''}
          `}
          title={isOnline ? 'Open AstroGeo AI' : 'Chatbot offline'}
          aria-label="Open AstroGeo AI chat"
        >
          {isOpen ? (
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
          )}
        </motion.button>
      </div>

      {/* Chat Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            id="chat-widget-panel"
            key="chat-panel"
            initial={{ opacity: 0, y: 24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed bottom-24 right-6 z-50 w-[380px] h-[540px] flex flex-col rounded-2xl overflow-hidden shadow-2xl border border-slate-700/80 bg-[#0e121e]"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-[#0e1830] to-[#131a2e] border-b border-slate-700/60">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center text-sm shadow-[0_0_10px_rgba(34,211,238,0.4)]">
                  🌌
                </div>
                <div>
                  <div className="text-sm font-bold text-white tracking-wide">AstroGeo AI</div>
                  <div className="text-[10px] text-slate-500">Powered by OpenAI GPT-4o</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
                  <span className="text-[10px] text-emerald-400 font-medium">Online</span>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  id="chat-widget-close"
                  className="text-slate-500 hover:text-white transition-colors p-1 rounded"
                  aria-label="Close chat"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Messages area */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 scroll-smooth">
              {messages.length === 0 && !loading && (
                <div className="flex flex-col items-center justify-center h-full gap-5 text-center">
                  <div className="text-3xl">🛰️</div>
                  <div>
                    <p className="text-sm text-slate-300 font-medium mb-1">AstroGeo AI is ready</p>
                    <p className="text-xs text-slate-500 max-w-[260px]">
                      Ask about live asteroids, launch probability, vegetation data, or cross-domain insights.
                    </p>
                  </div>

                  {/* Suggestion chips */}
                  <div className="flex flex-col gap-2 w-full mt-2">
                    {SUGGESTION_CHIPS.map((chip, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(chip.label)}
                        className="text-left text-xs px-3 py-2 rounded-xl bg-slate-800/60 border border-slate-700/60 text-slate-300 hover:bg-slate-700/80 hover:text-white hover:border-cyan-500/40 transition-all flex items-center gap-2"
                      >
                        <span>{chip.icon}</span>
                        <span>{chip.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center text-[10px] mr-2 mt-0.5 flex-shrink-0">
                      🌌
                    </div>
                  )}
                  <div
                    className={`max-w-[85%] text-xs leading-relaxed rounded-2xl px-3 py-2 whitespace-pre-wrap ${
                      msg.role === 'user'
                        ? 'bg-indigo-600/80 text-white rounded-tr-sm'
                        : 'bg-slate-800/70 text-slate-200 border border-slate-700/60 rounded-tl-sm'
                    }`}
                  >
                    {msg.content}
                  </div>
                </motion.div>
              ))}

              {loading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex justify-start"
                >
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center text-[10px] mr-2 mt-0.5 flex-shrink-0">
                    🌌
                  </div>
                  <TypingIndicator />
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="px-3 py-3 border-t border-slate-700/60 bg-[#0a0e17]">
              <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700/60 rounded-xl px-3 py-2 focus-within:border-cyan-500/50 transition-colors">
                <input
                  ref={inputRef}
                  id="chat-widget-input"
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={loading}
                  placeholder={loading ? 'Thinking...' : 'Ask AstroGeo AI...'}
                  className="flex-1 bg-transparent text-xs text-slate-200 placeholder:text-slate-600 outline-none disabled:opacity-60"
                />
                <button
                  id="chat-widget-send"
                  onClick={() => sendMessage()}
                  disabled={loading || !input.trim()}
                  className="w-7 h-7 flex items-center justify-center rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                  aria-label="Send message"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
