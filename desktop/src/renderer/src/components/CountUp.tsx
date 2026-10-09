import { useEffect, useRef, useState } from 'react'

const reduceMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

// Counts from the previous value (0 on first show) to `value` with an ease-out.
export function CountUp({ value, duration = 800, format = String }: { value: number; duration?: number; format?: (n: number) => string }) {
  const [shown, setShown] = useState(reduceMotion() ? value : 0)
  const from = useRef(shown)

  useEffect(() => {
    if (reduceMotion()) {
      setShown(value)
      return
    }
    const start = performance.now()
    const begin = from.current
    let raf = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration)
      const v = Math.round(begin + (value - begin) * (1 - (1 - p) ** 3))
      setShown(v)
      from.current = v
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value, duration])

  return <span className="tabular-nums">{format(shown)}</span>
}
