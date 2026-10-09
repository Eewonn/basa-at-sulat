import { Fragment, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { Volume2, VolumeX, X } from 'lucide-react'
import { api } from '@/api'
import { isMuted, setMuted, sfx } from '@/audio/sfx'
import { useRecorder } from '@/audio/useRecorder'
import { Confetti, ConfettiRain } from '@/components/Confetti'
import { Emoji } from '@/components/Emoji'
import { Stamp } from '@/components/Stamp'
import { LiveWaveform } from '@/components/LiveWaveform'
import { Tamaraw, type Mood } from '@/components/Tamaraw'
import { useT } from '@/strings'

type Phase = 'ready' | 'hearing' | 'listening' | 'checking' | 'retry' | 'correct'

const pick = (list: string[]) => list[Math.floor(Math.random() * list.length)]

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
      className="relative grid size-12 cursor-pointer place-items-center overflow-hidden rounded-full bg-white text-muted shadow-soft"
    >
      <span
        className="absolute inset-x-0 bottom-0 bg-coral/40"
        style={{ height: holding ? '100%' : '0%', transition: holding ? 'height 2s linear' : 'height 150ms' }}
      />
      <X className="relative size-5" strokeWidth={3} />
    </button>
  )
}

// Progress as stepping stones; a little Taw hops to the next stone after each word.
function StonePath({ total, at }: { total: number; at: number }) {
  const stones = total + 1 // the words, plus the reread step
  const step = 76
  return (
    <div className="relative h-24" style={{ width: stones * step + 60 }} aria-hidden>
      {Array.from({ length: stones }, (_, i) => (
        <span
          key={i}
          className={`absolute bottom-2 h-5 w-14 rounded-[50%] transition-colors duration-500 ${i < at ? 'bg-teal' : i === at ? 'bg-blue' : 'bg-banig'}`}
          style={{ left: i * step }}
        />
      ))}
      <svg className="absolute bottom-2" style={{ left: stones * step + 6 }} width="40" height="56" viewBox="0 0 40 56">
        <rect x="4" y="4" width="4" height="50" rx="2" fill="#1E2A5A" />
        <path d="M8 6 L36 14 L8 24 Z" fill={at >= stones ? '#FFB627' : '#D62F55'} />
      </svg>
      <span key={at} className="absolute bottom-5 animate-hop transition-[left] duration-500 ease-out" style={{ left: Math.min(at, stones) * step - 4 }}>
        <Tamaraw size={64} mood={at >= stones ? 'happy' : 'idle'} />
      </span>
    </div>
  )
}

function Bubble({ text }: { text: string }) {
  return (
    <p key={text} className="relative animate-pop rounded-tile bg-white px-4 py-2 text-center text-lg font-black text-navy shadow-soft">
      {text}
      <span className="absolute -bottom-2 left-1/2 size-4 -translate-x-1/2 rotate-45 bg-white" aria-hidden />
    </p>
  )
}

export function PracticeScreen() {
  const t = useT()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { learnerId = 'l_01' } = useParams()
  const { data: items } = useQuery({ queryKey: ['practice', learnerId], queryFn: () => api.practice(learnerId), staleTime: 0, gcTime: 0 })
  const { data: stats } = useQuery({ queryKey: ['stats', learnerId], queryFn: () => api.learnerStats(learnerId) })
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  const name = learners?.find((l) => l.id === learnerId)?.display_name ?? ''
  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState<Phase>('ready')
  const [earned, setEarned] = useState(0)
  const [burst, setBurst] = useState(0)
  const [cheer, setCheer] = useState('')
  const [bubble, setBubble] = useState('')
  const [streak, setStreak] = useState(0)
  const [comboShown, setComboShown] = useState(0)
  const [firstTry, setFirstTry] = useState(true)
  const [talk, setTalk] = useState(0)
  const [muted, setMutedState] = useState(isMuted)
  const [flight, setFlight] = useState<{ x: number; y: number; dx: number; dy: number } | null>(null)
  const counter = useRef<HTMLDivElement>(null)
  const card = useRef<HTMLDivElement>(null)
  const rec = useRecorder()
  const doneRef = useRef(false)

  // Taw greets the child by name once the page knows who it is.
  useEffect(() => {
    if (name) setBubble(t.kidHello(name))
  }, [name, t])

  // Taw's mouth and ears follow the child's voice while recording.
  useEffect(() => {
    const analyser = rec.analyser
    if (!analyser || phase !== 'listening') {
      setTalk(0)
      return
    }
    const buf = new Uint8Array(analyser.fftSize)
    let raf = 0
    const tick = () => {
      analyser.getByteTimeDomainData(buf)
      let sum = 0
      for (const v of buf) sum += ((v - 128) / 128) ** 2
      setTalk(Math.min(1, Math.sqrt(sum / buf.length) * 6))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [rec.analyser, phase])

  const step = items ? (index < items.length ? 'word' : index === items.length ? 'reread' : 'done') : 'word'

  // The big finish: fanfare, then each earned star lands with a sparkle.
  useEffect(() => {
    if (step !== 'done' || doneRef.current) return
    doneRef.current = true
    setBubble(t.kidDone(name))
    sfx.fanfare()
    const timer = setTimeout(sfx.stamp, 850)
    return () => clearTimeout(timer)
  }, [step, earned, name, t])

  if (!items) return <div className="h-full bg-kid" />
  const item = items[Math.min(index, items.length - 1)]

  const flyStar = () => {
    const from = card.current?.getBoundingClientRect()
    const to = counter.current?.getBoundingClientRect()
    if (!from || !to) return
    const x = from.left + from.width / 2 - 24
    const y = from.top + from.height / 2 - 24
    setFlight({ x, y, dx: to.left + 8 - x, dy: to.top + 4 - y })
    setTimeout(() => {
      setFlight(null)
      sfx.sparkle()
    }, 700)
  }

  const hear = () => {
    // Mockup: the real app plays the fluent speaker's clip from the Sulat recording.
    sfx.pop()
    setPhase('hearing')
    setTimeout(() => setPhase('ready'), 900)
  }

  const say = async () => {
    setBubble(t.kidListen)
    setPhase('listening')
    await rec.start()
    setTimeout(async () => {
      const audio = await rec.stop()
      setPhase('checking')
      const { result } = await api.checkWord(audio, item.word, learnerId)
      if (result === 'match') {
        const nextStreak = firstTry ? streak + 1 : 0
        setStreak(nextStreak)
        setCheer(pick(t.cheersRight))
        setBubble(t.kidRight(name))
        setPhase('correct')
        setBurst((b) => b + 1)
        if (nextStreak >= 2) {
          setComboShown(nextStreak)
          sfx.combo()
        } else sfx.chime()
        flyStar()
        setTimeout(() => setEarned((e) => e + 1), 650)
        qc.invalidateQueries({ queryKey: ['stats', learnerId] })
        setTimeout(() => {
          setPhase('ready')
          setComboShown(0)
          setFirstTry(true)
          setIndex((i) => i + 1)
        }, 1500)
      } else {
        sfx.boing()
        setStreak(0)
        setFirstTry(false)
        setCheer(pick(t.cheersRetry))
        setBubble(t.kidRetry(name))
        setPhase('retry')
      }
    }, 1800)
  }

  const busy = phase === 'hearing' || phase === 'listening' || phase === 'checking'

  return (
    <div className="relative flex h-full flex-col items-center justify-center gap-8 overflow-hidden bg-kid banig-light px-10">
      <div className="absolute inset-x-5 top-5 flex items-start justify-between">
        <div ref={counter} className="flex items-center gap-2 rounded-full bg-white py-2 pr-5 pl-3 shadow-soft">
          <Emoji name="star" size={32} />
          <span key={stats?.stars} className="animate-pop text-2xl font-black text-navy tabular-nums">
            {stats?.stars ?? 0}
          </span>
        </div>
        {step !== 'done' && <StonePath total={items.length} at={index} />}
        <div className="flex gap-3">
          <button
            onClick={() => {
              setMuted(!muted)
              setMutedState(!muted)
            }}
            aria-label={t.sound}
            title={t.sound}
            className="grid size-12 cursor-pointer place-items-center rounded-full bg-white text-navy shadow-soft"
          >
            {muted ? <VolumeX className="size-5" /> : <Volume2 className="size-5" />}
          </button>
          <HoldToExit onExit={() => navigate(`/learner/${learnerId}`)} label={t.holdToExit} />
        </div>
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

      {step === 'word' && (
        <>
          <div className="relative mt-16 flex items-center gap-8">
            <div className="flex w-56 flex-col items-center gap-3">
              {bubble && <Bubble text={bubble} />}
              <Tamaraw key={`${index}-${phase}`} mood={MOOD[phase]} size={190} talk={phase === 'listening' ? talk : undefined} />
            </div>
            <div
              ref={card}
              key={`${index}-${phase === 'retry' ? 'r' : ''}`}
              className={`flashcard relative flex min-w-[480px] flex-col items-center rounded-[10px] px-16 pt-12 pb-8 shadow-lift ${
                phase === 'correct' ? 'ring-4 ring-teal' : ''
              } ${phase === 'retry' ? 'animate-shake ring-4 ring-coral' : 'animate-pop'}`}
            >
              <span className="absolute top-3 left-1/2 flex -translate-x-1/2 gap-24" aria-hidden>
                <span className="size-4 rounded-full bg-kid shadow-[inset_0_2px_3px_rgba(30,42,90,0.35)]" />
                <span className="size-4 rounded-full bg-kid shadow-[inset_0_2px_3px_rgba(30,42,90,0.35)]" />
              </span>
              {phase === 'correct' && <Confetti key={burst} count={comboShown ? 44 : 28} />}
              {comboShown >= 2 && (
                <span className="absolute -top-6 right-6 flex animate-pop items-center gap-1 rounded-full bg-sun px-4 py-2 text-xl font-black text-navy shadow-lift">
                  <Emoji name="fire" size={28} /> {t.combo(comboShown)}
                </span>
              )}
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
          <p className="mt-16 text-2xl font-black text-blue">{t.rereadTitle}</p>
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
            onClick={() => {
              sfx.pop()
              setIndex((i) => i + 1)
            }}
            className="h-20 cursor-pointer rounded-full bg-blue px-16 text-[28px] font-black text-white shadow-lift transition hover:-translate-y-1"
          >
            {t.next}
          </button>
        </>
      )}

      {step === 'done' && (
        <>
          <ConfettiRain />
          <div className="relative z-20 flex flex-col items-center gap-3">
            {bubble && <Bubble text={bubble} />}
            <Tamaraw mood="happy" size={220} dance />
          </div>
          <Stamp size={190} className="relative z-20 -my-4" />
          <div className="relative z-20 text-center">
            <p className="text-6xl font-black text-navy">{t.done}</p>
            <p className="mt-3 flex items-center justify-center gap-2 text-2xl font-extrabold text-body">
              <Emoji name="glowingStar" size={40} /> {t.starsEarned(earned)}
            </p>
          </div>
          <button
            onClick={() => navigate(`/learner/${learnerId}`)}
            className="relative z-20 h-16 cursor-pointer rounded-full bg-blue px-12 text-xl font-black text-white shadow-lift hover:bg-blue-dark"
          >
            {t.back}
          </button>
        </>
      )}
    </div>
  )
}
