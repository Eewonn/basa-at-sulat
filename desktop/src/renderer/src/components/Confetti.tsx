import { useMemo } from 'react'

const COLORS = ['#2D5BD3', '#D62F55', '#17885A', '#FFB627', '#7B3FF2']

// A one-shot burst. Re-mount (change `key`) to fire again.
export function Confetti({ count = 28 }: { count?: number }) {
  const pieces = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => {
        const angle = (i / count) * Math.PI * 2
        const dist = 140 + Math.random() * 120
        return {
          color: COLORS[i % COLORS.length],
          dx: `${Math.cos(angle) * dist}px`,
          dy: `${Math.sin(angle) * dist + 80}px`,
          rot: `${Math.random() * 720 - 360}deg`,
          round: i % 3 === 0
        }
      }),
    [count]
  )
  return (
    <div className="pointer-events-none absolute top-1/2 left-1/2 z-20" aria-hidden>
      {pieces.map((p, i) => (
        <span
          key={i}
          className={`absolute block size-3 animate-confetti ${p.round ? 'rounded-full' : 'rounded-[2px]'}`}
          style={{ background: p.color, ['--dx' as string]: p.dx, ['--dy' as string]: p.dy, ['--rot' as string]: p.rot }}
        />
      ))}
    </div>
  )
}

// Confetti falling from the top of the screen, for the finish screen.
export function ConfettiRain({ count = 70 }: { count?: number }) {
  const pieces = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        color: COLORS[i % COLORS.length],
        left: `${Math.random() * 100}%`,
        delay: `${Math.random() * 1.6}s`,
        dur: `${2.4 + Math.random() * 1.8}s`,
        rot: `${Math.random() * 900 - 450}deg`,
        round: i % 3 === 0
      })),
    [count]
  )
  return (
    <div className="pointer-events-none fixed inset-0 z-10 overflow-hidden" aria-hidden>
      {pieces.map((p, i) => (
        <span
          key={i}
          className={`rain absolute top-0 block size-3 ${p.round ? 'rounded-full' : 'rounded-[2px]'}`}
          style={{ left: p.left, background: p.color, ['--delay' as string]: p.delay, ['--dur' as string]: p.dur, ['--rot' as string]: p.rot }}
        />
      ))}
    </div>
  )
}
