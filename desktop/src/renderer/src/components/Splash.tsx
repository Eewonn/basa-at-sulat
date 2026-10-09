import { useEffect, useState } from 'react'
import { TawLogo } from './TawLogo'
import { useT } from '@/strings'

// Shown on every launch while the app loads behind it. A click or any key skips it.
export function Splash({ onDone }: { onDone: () => void }) {
  const t = useT()
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    const quick = matchMedia('(prefers-reduced-motion: reduce)').matches
    const timer = setTimeout(() => setLeaving(true), quick ? 900 : 2300)
    const skip = () => setLeaving(true)
    window.addEventListener('keydown', skip)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('keydown', skip)
    }
  }, [])

  useEffect(() => {
    if (!leaving) return
    const timer = setTimeout(onDone, 380)
    return () => clearTimeout(timer)
  }, [leaving, onDone])

  return (
    <div
      onClick={() => setLeaving(true)}
      className={`paper fixed inset-0 z-[100] flex flex-col items-center justify-center bg-kid ${leaving ? 'animate-splash-out' : ''}`}
      role="status"
      aria-label={t.appName}
    >
      <div className="animate-splash-drop">
        <TawLogo size={280} className="animate-float [animation-delay:900ms]" />
      </div>
      <h1 className="mt-2 animate-write font-hand text-[72px] leading-none text-navy">{t.appName}</h1>
      <p className="mt-3 animate-fade-in text-xl font-bold text-body [animation-delay:1200ms]">{t.splashTag}</p>
      <div className="mt-10 flex gap-2.5" aria-hidden>
        {['bg-blue', 'bg-coral', 'bg-teal'].map((c, i) => (
          <span key={c} className={`size-3 animate-dot rounded-full ${c}`} style={{ animationDelay: `${i * 160}ms` }} />
        ))}
      </div>
    </div>
  )
}
