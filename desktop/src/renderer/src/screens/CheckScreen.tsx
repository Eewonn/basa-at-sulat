import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { ArrowLeft, Check, Lock, Loader2, Mic, MicOff, Square } from 'lucide-react'
import { api } from '@/api'
import type { Passage } from '@/api/types'
import { useRecorder } from '@/audio/useRecorder'
import { LiveWaveform } from '@/components/LiveWaveform'
import { useT } from '@/strings'

function Processing() {
  const t = useT()
  const [ms, setMs] = useState(0)
  useEffect(() => {
    const started = Date.now()
    const id = setInterval(() => setMs(Date.now() - started), 100)
    return () => clearInterval(id)
  }, [])
  const stages = [t.stagePrep, t.stageAlign, t.stageScore]
  const current = ms < 600 ? 0 : ms < 1400 ? 1 : 2

  return (
    <div className="mx-auto flex max-w-md flex-col gap-4 py-16">
      {stages.map((s, i) => (
        <div key={s} className={`flex items-center gap-3 text-lg font-bold ${i <= current ? 'text-ink' : 'text-muted/60'}`}>
          {i < current ? (
            <Check className="size-6 text-correct" aria-hidden />
          ) : i === current ? (
            <Loader2 className="size-6 animate-spin text-accent" aria-hidden />
          ) : (
            <span className="size-6 rounded-full ring-2 ring-line" aria-hidden />
          )}
          {s}
        </div>
      ))}
      {ms > 10_000 && <p className="text-muted">{t.stageSlow}</p>}
    </div>
  )
}

export function CheckScreen() {
  const t = useT()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { learnerId = 'l_01' } = useParams()
  const [passage, setPassage] = useState<Passage | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const rec = useRecorder()
  const { data: passages } = useQuery({ queryKey: ['passages'], queryFn: () => api.passages() })
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  const learner = learners?.find((l) => l.id === learnerId)

  const assess = useMutation({
    mutationFn: (audio: Blob) => api.assess(audio, learnerId, passage!.id),
    onSuccess: (a) => {
      qc.setQueryData(['assessment', a.assessment_id], a)
      navigate(`/review/${a.assessment_id}`)
    }
  })

  useEffect(() => {
    if (rec.state !== 'recording') return
    const started = Date.now()
    const id = setInterval(() => setElapsed((Date.now() - started) / 1000), 200)
    return () => clearInterval(id)
  }, [rec.state])

  const toggle = async () => {
    if (rec.state === 'recording') assess.mutate(await rec.stop())
    else {
      setElapsed(0)
      await rec.start()
    }
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === 'Space' && passage && !assess.isPending) {
        e.preventDefault()
        toggle()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  return (
    <div className="mx-auto max-w-5xl px-10 py-10">
      <button onClick={() => (passage ? setPassage(null) : navigate('/'))} className="flex cursor-pointer items-center gap-2 font-bold text-muted hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden /> {learner?.display_name ?? ''}
      </button>

      {!passage && (
        <>
          <h1 className="mt-4 font-display text-4xl font-bold text-ink">{t.pickPassage}</h1>
          <div className="mt-8 grid grid-cols-2 gap-5">
            {passages?.map((p) => (
              <button
                key={p.id}
                onClick={() => setPassage(p)}
                className="cursor-pointer rounded-card bg-card p-6 text-left ring-1 ring-line transition hover:shadow-soft hover:ring-accent-light"
              >
                <div className="flex gap-2 text-xs font-extrabold tracking-wider text-muted uppercase">
                  <span>{p.language === 'fil' ? 'Filipino' : 'English'}</span>·<span>Grade {p.grade}</span>·
                  <span>
                    {p.text.split(/\s+/).length} {t.words}
                  </span>
                </div>
                <p className="mt-2 font-display text-2xl font-bold text-ink">{p.title}</p>
                <p className="mt-2 line-clamp-2 text-body">{p.text}</p>
              </button>
            ))}
          </div>
        </>
      )}

      {passage && assess.isPending && <Processing />}

      {passage && !assess.isPending && (
        <div className="mt-4 flex flex-col gap-8">
          <div>
            <h1 className="font-display text-4xl font-bold text-ink">{t.recordTitle}</h1>
            <p className="mt-1 text-body">{t.recordHint}</p>
          </div>
          <p className="rounded-card bg-card p-8 font-display text-[34px] leading-relaxed font-bold text-ink ring-1 ring-line">{passage.text}</p>

          {rec.state === 'blocked' ? (
            <div className="flex items-start gap-3 rounded-card bg-accent-bg p-5 text-[#8a3d12]">
              <MicOff className="mt-0.5 size-6 shrink-0" aria-hidden />
              <div>
                <p className="font-bold">{t.micBlocked}</p>
                <p className="mt-1 text-sm">{window.basa?.platform === 'win32' ? t.micBlockedFixWin : t.micBlockedFixLinux}</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-6">
              <button
                onClick={toggle}
                className={`flex size-24 shrink-0 cursor-pointer items-center justify-center rounded-full text-paper transition ${
                  rec.state === 'recording' ? 'animate-ring bg-accent' : 'bg-ink hover:bg-ink-2'
                }`}
                aria-label={rec.state === 'recording' ? t.recordStop : t.recordStart}
              >
                {rec.state === 'recording' ? <Square className="size-9 fill-current" /> : <Mic className="size-10" />}
              </button>
              <div className="min-w-0 flex-1">
                <LiveWaveform analyser={rec.analyser} />
                <div className="mt-2 flex items-center justify-between text-sm">
                  <span className="font-bold text-ink tabular-nums">
                    {rec.state === 'recording' ? `● ${elapsed.toFixed(1)} s` : t.recordStart}
                  </span>
                  <span className="flex items-center gap-1.5 text-muted">
                    <Lock className="size-3.5" aria-hidden /> {t.recordPrivacy}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
