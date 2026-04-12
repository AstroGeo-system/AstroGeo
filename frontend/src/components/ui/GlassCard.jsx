'use client'

import { motion } from 'framer-motion'

function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

export default function GlassCard({
  className,
  children,
  hover = true,
  animate = true,
}) {
  const Comp = animate ? motion.div : 'div'
  const props = animate
    ? {
        initial: { opacity: 0, y: 10 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.35, ease: [0.2, 0.8, 0.2, 1] },
      }
    : {}

  return (
    <Comp
      {...props}
      className={cn(
        'glass glow-outline',
        hover && 'glass-hover hover:glow-soft',
        className
      )}
    >
      {children}
    </Comp>
  )
}

