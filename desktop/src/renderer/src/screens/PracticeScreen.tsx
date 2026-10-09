import { Fragment, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { Check, Mic, Star, Volume2, X } from 'lucide-react'
import { api } from '@/api'
import { useRecorder } from '@/audio/useRecorder'
import { LiveWaveform } from '@/components/LiveWaveform'
import { useT } from '@/strings'

type Phase = 'ready' | 'hearing' | 'listening' | 'checking' | 'retry' | 'correct'

// Teacher-only exit: hold for 2 seconds so a child can't leave by accident.
function HoldToExit({ onExit, label }: { onExit: () => void; label: string }) {
  const [holding, setHolding] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined)
  const begin = () => {
    setHolding(true)
    timer.current = setTimeout(onExit, 2000)
  }
  const cancel = () => {
    setHolding(false)
    clearTimeout(timer.current)
  }
  return (
    <button
      onPointerDown={begin}
      onPointerUp={cancel}
      onPointerLeave={cancel}
      aria-label={label}
      title={label}
      className="absolute top-5 right-5 grid size-12 cursor-pointer place-items-center overflow-hidden rounded-full bg-paper-2 text-muted ring-1 ring-line"
    >
      <span
        className="absolute inset-x-0 bottom-0 bg-accent-light/60"
        style={{ height: holding ? '100%' : '0%', transition: holding ? 'height 2s linear' : 'height 150ms' }}
      />
      <X className="relative size-5" />
    </button>
  )
}

export function PracticeScreen() {
  const t = useT()
  const navigate = useNavigate()
  const { learnerId = 'l_01' } = useParams()
  const { data: items } = useQuery({ queryKey: ['practice', learnerId], queryFn: () => api.practice(learnerId) })
  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState<Phase>('ready')
  const rec = useRecorder()

  if (!items) return <div className="h-full bg-paper" />
  const step = index < items.length ? 'word' : index === items.length ? 'reread' : 'done'
  const item = items[Math.min(index, items.length - 1)]

  const hear = () => {
    // Mockup: the real app plays the fluent speaker's clip from the Sulat recording.
    setPhase('hearing')
    setTimeout(() => setPhase('ready'), 900)
  }

  const say = async () => {
    setPhase('listening')
    await rec.start()
    setTimeout(async () => {
      const audio = await rec.stop()
      setPhase('checking')
      const { result } = await api.checkWord(audio, item.word)
      if (result === 'match') {
        setPhase('correct')
        setTimeout(() => {
          setPhase('ready')
          setIndex((i) => i + 1)
        }, 1100)
      } else setPhase('retry')
    }, 1800)
  }

  const busy = phase === 'hearing' || phase === 'listening' || phase === 'checking'

  return (
    <div className="relative flex h-full flex-col items-center justify-center gap-10 bg-paper px-10">
      <HoldToExit onExit={() => navigate('/')} label={t.holdToExit} />

      {step !== 'done' && (
        <div className="absolute top-7 flex gap-2" aria-hidden>
          {[...items, null].map((_, i) => (
            <span key={i} className={`h-2.5 w-10 rounded-full ${i < index ? 'bg-correct' : i === index ? 'bg-accent' : 'bg-line'}`} />
          ))}
        </div>
      )}

      {step === 'word' && (
        <>
          <div
            key={`${index}-${phase === 'retry' ? 'r' : ''}`}
            className={`flex min-w-[520px] flex-col items-center rounded-[28px] bg-card px-16 py-12 shadow-soft ${
              phase === 'correct' ? 'ring-4 ring-correct' : 'ring-1 ring-line'
            } ${phase === 'retry' ? 'animate-shake' : ''}`}
          >
            <p className="font-display text-[120px] leading-none font-bold text-ink">{item.word}</p>
            <div className="mt-6 h-10">
              {phase === 'retry' && <p className="text-2xl font-extrabold text-[#8a3d12]">{t.tryAgain}</p>}
              {phase === 'correct' && (
                <p className="flex animate-pop items-center gap-2 text-3xl font-extrabold text-correct">
                  <Check className="size-8" aria-hidden /> {t.gotIt}
                </p>
              )}
              {phase === 'listening' && <LiveWaveform analyser={rec.analyser} color="#1F6F6B" height={40} />}
              {phase === 'checking' && <p className="text-xl font-bold text-muted">…</p>}
            </div>
          </div>
          <div className="flex gap-6">
            <button
              onClick={hear}
              disabled={busy}
              className={`flex h-28 w-60 cursor-pointer flex-col items-center justify-center gap-1 rounded-[24px] bg-correct text-2xl font-extrabold text-paper transition hover:brightness-110 disabled:opacity-60 ${
                phase === 'hearing' ? 'animate-pulse' : ''
              }`}
            >
              <Volume2 className="size-10" aria-hidden /> {t.hearIt}
            </button>
            <button
              onClick={say}
              disabled={busy}
              className={`flex h-28 w-60 cursor-pointer flex-col items-center justify-center gap-1 rounded-[24px] bg-accent text-2xl font-extrabold text-paper transition hover:brightness-110 disabled:opacity-60 ${
                phase === 'listening' ? 'animate-ring' : ''
              }`}
            >
              <Mic className="size-10" aria-hidden /> {phase === 'listening' ? t.listening : t.sayIt}
            </button>
          </div>
        </>
      )}

      {step === 'reread' && (
        <>
          <p className="text-2xl font-extrabold text-muted">{t.rereadTitle}</p>
          <p className="max-w-4xl text-center font-display text-5xl leading-snug font-bold text-ink">
            {item.sentence.split(/\s+/).map((w, i) => {
              const hit = items.some((it) => w.replace(/[.,]/g, '') === it.word)
              return (
                <Fragment key={i}>
                  <span className={hit ? 'rounded-lg bg-accent-bg px-1.5 text-ink ring-2 ring-accent' : ''}>{w}</span>{' '}
                </Fragment>
              )
            })}
          </p>
          <button
            onClick={() => setIndex((i) => i + 1)}
            className="h-20 cursor-pointer rounded-[24px] bg-ink px-14 text-2xl font-extrabold text-paper transition hover:bg-ink-2"
          >
            {t.next}
          </button>
        </>
      )}

      {step === 'done' && (
        <>
          <div className="flex gap-4">
            {[0, 1, 2].map((i) => (
              <Star key={i} className="size-24 animate-pop fill-accent-light text-accent" style={{ animationDelay: `${i * 150}ms` }} aria-hidden />
            ))}
          </div>
          <div className="text-center">
            <p className="font-display text-6xl font-bold text-ink">{t.done}</p>
            <p className="mt-2 text-xl text-body">{t.doneSub}</p>
          </div>
          <button onClick={() => navigate('/')} className="h-16 cursor-pointer rounded-[20px] bg-ink px-10 text-xl font-bold text-paper hover:bg-ink-2">
            {t.backToClass}
          </button>
        </>
      )}
    </div>
  )
}
