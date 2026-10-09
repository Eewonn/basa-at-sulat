import { useMemo } from 'react'

const COLORS = ['#3D63E8', '#EE4466', '#12A08A', '#FFC531', '#7B3FF2']

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
