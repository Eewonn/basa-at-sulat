import { Fragment, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { X } from 'lucide-react'
import { api } from '@/api'
import { useRecorder } from '@/audio/useRecorder'
import { Confetti } from '@/components/Confetti'
import { Emoji } from '@/components/Emoji'
import { LiveWaveform } from '@/components/LiveWaveform'
import { Tamaraw, type Mood } from '@/components/Tamaraw'
import { useT } from '@/strings'

const pick = (list: string[]) => list[Math.floor(Math.random() * list.length)]

type Phase = 'ready' | 'hearing' | 'listening' | 'checking' | 'retry' | 'correct'

const MOOD: Record<Phase, Mood> = {
  ready: 'idle',
  hearing: 'listening',
  listening: 'listening',
  checking: 'thinking',
  retry: 'encourage',
  correct: 'happy'
}

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
      className="absolute top-5 right-5 grid size-12 cursor-pointer place-items-center overflow-hidden rounded-full bg-white text-muted shadow-soft"
    >
      <span
        className="absolute inset-x-0 bottom-0 bg-coral/40"
        style={{ height: holding ? '100%' : '0%', transition: holding ? 'height 2s linear' : 'height 150ms' }}
      />
      <X className="relative size-5" strokeWidth={3} />
    </button>
  )
}

export function PracticeScreen() {
  const t = useT()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { learnerId = 'l_01' } = useParams()
  const { data: items } = useQuery({ queryKey: ['practice', learnerId], queryFn: () => api.practice(learnerId) })
  const { data: stats } = useQuery({ queryKey: ['stats', learnerId], queryFn: () => api.learnerStats(learnerId) })
  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState<Phase>('ready')
  const [earned, setEarned] = useState(0)
  const [cheer, setCheer] = useState('')
  const [burst, setBurst] = useState(0)
  const [flight, setFlight] = useState<{ x: number; y: number; dx: number; dy: number } | null>(null)
  const counter = useRef<HTMLDivElement>(null)
  const card = useRef<HTMLDivElement>(null)
  const rec = useRecorder()

  if (!items) return <div className="h-full bg-kid" />
  const step = index < items.length ? 'word' : index === items.length ? 'reread' : 'done'
  const item = items[Math.min(index, items.length - 1)]

  const flyStar = () => {
    const from = card.current?.getBoundingClientRect()
    const to = counter.current?.getBoundingClientRect()
    if (!from || !to) return
    const x = from.left + from.width / 2 - 24
    const y = from.top + from.height / 2 - 24
    setFlight({ x, y, dx: to.left + 8 - x, dy: to.top + 4 - y })
    setTimeout(() => setFlight(null), 700)
  }

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
      const { result } = await api.checkWord(audio, item.word, learnerId)
      if (result === 'match') {
        setCheer(pick(t.cheersRight))
        setPhase('correct')
        setBurst((b) => b + 1)
        flyStar()
        setTimeout(() => setEarned((e) => e + 1), 650)
        qc.invalidateQueries({ queryKey: ['stats', learnerId] })
        setTimeout(() => {
          setPhase('ready')
          setIndex((i) => i + 1)
        }, 1300)
      } else {
        setCheer(pick(t.cheersRetry))
        setPhase('retry')
      }
    }, 1800)
  }

  const busy = phase === 'hearing' || phase === 'listening' || phase === 'checking'
  const totalStars = stats?.stars ?? 0

  return (
    <div className="relative flex h-full flex-col items-center justify-center gap-10 overflow-hidden bg-kid banig-light px-10">
      <HoldToExit onExit={() => navigate(`/learner/${learnerId}`)} label={t.holdToExit} />

      <div ref={counter} className="absolute top-5 left-5 flex items-center gap-2 rounded-full bg-white py-2 pr-5 pl-3 shadow-soft">
        <Emoji name="star" size={32} />
        <span key={totalStars} className="animate-pop text-2xl font-black text-navy tabular-nums">
          {totalStars}
        </span>
      </div>

      {flight && (
        <span
          className="pointer-events-none fixed z-30 animate-fly"
          style={{ left: flight.x, top: flight.y, ['--dx' as string]: `${flight.dx}px`, ['--dy' as string]: `${flight.dy}px` }}
          aria-hidden
        >
          <Emoji name="star" size={48} />
        </span>
      )}

      {step !== 'done' && (
        <div className="absolute top-8 flex gap-2" aria-hidden>
          {[...items, null].map((_, i) => (
            <span key={i} className={`h-3 w-12 rounded-full ${i < index ? 'bg-teal' : i === index ? 'bg-blue' : 'bg-blue-soft'}`} />
          ))}
        </div>
      )}

      {step === 'word' && (
        <>
          <div className="relative flex items-center gap-8">
            <Tamaraw key={`${index}-${phase}`} mood={MOOD[phase]} size={200} />
            <div
              ref={card}
              key={`${index}-${phase === 'retry' ? 'r' : ''}`}
              className={`relative flex min-w-[480px] flex-col items-center rounded-[28px] bg-white px-16 py-10 shadow-lift ${
                phase === 'correct' ? 'ring-4 ring-teal' : ''
              } ${phase === 'retry' ? 'animate-shake ring-4 ring-coral' : ''}`}
            >
              {phase === 'correct' && <Confetti key={burst} />}
              <p className="text-[120px] leading-none font-black text-navy">{item.word}</p>
              <div className="mt-5 flex h-10 items-center">
                {phase === 'retry' && <p className="text-2xl font-black text-coral-ink">{cheer}</p>}
                {phase === 'correct' && <p className="animate-pop text-3xl font-black text-teal-ink">{cheer}</p>}
                {phase === 'listening' && <LiveWaveform analyser={rec.analyser} color="#2D5BD3" height={40} />}
                {phase === 'checking' && <p className="text-xl font-black text-muted">…</p>}
              </div>
            </div>
          </div>
          <div className="flex gap-6">
            <button
              onClick={hear}
              disabled={busy}
              className={`flex h-32 w-64 cursor-pointer flex-col items-center justify-center gap-1 rounded-[28px] bg-blue text-[28px] font-black text-white shadow-lift transition hover:-translate-y-1 disabled:opacity-60 ${
                phase === 'hearing' ? 'animate-pulse' : ''
              }`}
            >
              <Emoji name="speaker" size={52} /> {t.hearIt}
            </button>
            <button
              onClick={say}
              disabled={busy}
              className={`flex h-32 w-64 cursor-pointer flex-col items-center justify-center gap-1 rounded-[28px] bg-coral text-[28px] font-black text-white shadow-lift transition hover:-translate-y-1 disabled:opacity-60 ${
                phase === 'listening' ? 'animate-ring' : ''
              }`}
            >
              <Emoji name="microphone" size={52} /> {phase === 'listening' ? t.listening : t.sayIt}
            </button>
          </div>
        </>
      )}

      {step === 'reread' && (
        <>
          <p className="text-2xl font-black text-blue">{t.rereadTitle}</p>
          <p className="max-w-4xl text-center text-5xl leading-snug font-black text-navy">
            {item.sentence.split(/\s+/).map((w, i) => {
              const hit = items.some((it) => w.replace(/[.,]/g, '') === it.word)
              return (
                <Fragment key={i}>
                  <span className={hit ? 'rounded-xl bg-sun-soft px-2 ring-3 ring-sun' : ''}>{w}</span>{' '}
                </Fragment>
              )
            })}
          </p>
          <button
            onClick={() => setIndex((i) => i + 1)}
            className="h-20 cursor-pointer rounded-full bg-blue px-16 text-[28px] font-black text-white shadow-lift transition hover:-translate-y-1"
          >
            {t.next}
          </button>
        </>
      )}

      {step === 'done' && (
        <>
          <Confetti key="done" count={40} />
          <Tamaraw mood="happy" size={220} />
          <div className="text-center">
            <p className="text-6xl font-black text-navy">{t.done}</p>
            <p className="mt-3 flex items-center justify-center gap-2 text-2xl font-extrabold text-body">
              <Emoji name="glowingStar" size={40} /> {t.starsEarned(earned)}
            </p>
          </div>
          <button
            onClick={() => navigate(`/learner/${learnerId}`)}
            className="h-16 cursor-pointer rounded-full bg-blue px-12 text-xl font-black text-white shadow-lift hover:bg-blue-dark"
          >
            {t.back}
          </button>
        </>
      )}
    </div>
  )
}
