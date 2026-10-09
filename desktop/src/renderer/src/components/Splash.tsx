import { useEffect, useState } from 'react'
import { TawLogo } from './TawLogo'
import { useEngineState } from './EngineGate'
import { useT } from '@/strings'

// Shown on every launch, and doubles as the loading screen: it stays until the engine answers /health.
// Once the engine is up, a click or any key skips the rest of the intro.
export function Splash({ onDone }: { onDone: () => void }) {
  const t = useT()
  const engine = useEngineState()
  const [introDone, setIntroDone] = useState(false)
  const [skipped, setSkipped] = useState(false)
  const leaving = engine !== 'starting' && (introDone || skipped)

  useEffect(() => {
    const quick = matchMedia('(prefers-reduced-motion: reduce)').matches
    const timer = setTimeout(() => setIntroDone(true), quick ? 900 : 2300)
    const skip = () => setSkipped(true)
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
      onClick={() => setSkipped(true)}
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
      {introDone && engine === 'starting' && <p className="mt-4 animate-fade-in font-bold text-muted">{t.engineStartingTitle}</p>}
    </div>
  )
}
