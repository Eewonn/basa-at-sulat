import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { ArrowLeft, Check, Lock, Loader2, Mic, MicOff, Square } from 'lucide-react'
import { api } from '@/api'
import type { Category, Passage } from '@/api/types'
import { useRecorder } from '@/audio/useRecorder'
import { Emoji, type EmojiName } from '@/components/Emoji'
import { LiveWaveform } from '@/components/LiveWaveform'
import { Tamaraw } from '@/components/Tamaraw'
import { CategoryTile } from '@/components/ui'
import { useT } from '@/strings'

export const CATEGORY_EMOJI: Record<Category, EmojiName> = {
  bukid: 'rice',
  pamilya: 'house',
  hayop: 'buffalo',
  kalikasan: 'hibiscus',
  paaralan: 'school'
}

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
    <div className="flex flex-col items-center gap-6 py-12">
      <Tamaraw mood="thinking" size={180} />
      <p className="text-2xl font-black text-navy">{t.thinking(t.mascotName)}</p>
      <div className="flex flex-col gap-3">
        {stages.map((s, i) => (
          <div key={s} className={`flex items-center gap-3 text-lg font-extrabold ${i <= current ? 'text-navy' : 'text-muted/60'}`}>
            {i < current ? (
              <Check className="size-6 text-teal" strokeWidth={3} aria-hidden />
            ) : i === current ? (
              <Loader2 className="size-6 animate-spin text-blue" aria-hidden />
            ) : (
              <span className="size-6 rounded-full ring-2 ring-line" aria-hidden />
            )}
            {s}
          </div>
        ))}
      </div>
      {ms > 10_000 && <p className="font-semibold text-muted">{t.stageSlow}</p>}
    </div>
  )
}

export function CheckScreen() {
  const t = useT()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { learnerId = 'l_01' } = useParams()
  const [category, setCategory] = useState<Category | null>(null)
  const [passage, setPassage] = useState<Passage | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const rec = useRecorder()
  const { data: passages } = useQuery({ queryKey: ['passages'], queryFn: () => api.passages() })
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  const learner = learners?.find((l) => l.id === learnerId)
  const shown = passages?.filter((p) => !category || p.category === category)

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
    <div className="w-full max-w-[1680px] px-10 py-10">
      <button
        onClick={() => (passage ? setPassage(null) : navigate(`/learner/${learnerId}`))}
        className="flex cursor-pointer items-center gap-2 font-extrabold text-blue hover:text-blue-dark"
      >
        <ArrowLeft className="size-5" strokeWidth={3} aria-hidden /> {learner?.display_name ?? ''}
      </button>

      {!passage && (
        <>
          <h1 className="mt-3 text-[40px] leading-tight font-black text-navy">{t.pickStory}</h1>
          <h2 className="mt-6 text-xl font-extrabold text-navy">{t.categoriesTitle}</h2>
          <div className="mt-3 flex items-start gap-5">
            {(Object.keys(CATEGORY_EMOJI) as Category[]).map((c) => (
              <CategoryTile key={c} label={t.cat[c]} emoji={CATEGORY_EMOJI[c]} selected={category === c} onClick={() => setCategory(category === c ? null : c)} />
            ))}
            <button
              onClick={() => setCategory(null)}
              className="ml-auto cursor-pointer self-center rounded-tile px-6 py-3 font-extrabold text-purple ring-2 ring-purple transition hover:bg-[#f1eaff]"
            >
              {t.showAll}
            </button>
          </div>
          <div className="mt-8 grid grid-cols-[repeat(auto-fill,minmax(440px,1fr))] gap-5">
            {shown?.map((p) => (
              <button
                key={p.id}
                onClick={() => setPassage(p)}
                className="flex cursor-pointer gap-4 rounded-card bg-white p-5 text-left shadow-soft ring-1 ring-line transition hover:-translate-y-1 hover:shadow-lift"
              >
                <span className="grid size-16 shrink-0 place-items-center rounded-tile bg-blue-soft">
                  <Emoji name={CATEGORY_EMOJI[p.category]} size={40} />
                </span>
                <div className="min-w-0">
                  <div className="flex gap-2 text-xs font-extrabold tracking-wider text-muted uppercase">
                    <span>{p.language === 'fil' ? 'Filipino' : 'English'}</span>·<span>Grade {p.grade}</span>·
                    <span>
                      {p.text.split(/\s+/).length} {t.words}
                    </span>
                  </div>
                  <p className="mt-1 text-2xl font-black text-navy">{p.title}</p>
                  <p className="mt-1 line-clamp-2 font-semibold text-body">{p.text}</p>
                </div>
              </button>
            ))}
          </div>
        </>
      )}

      {passage && assess.isPending && <Processing />}

      {passage && !assess.isPending && (
        <div className="mt-3 flex max-w-5xl flex-col gap-8">
          <div>
            <h1 className="text-[40px] leading-tight font-black text-navy">{t.recordTitle}</h1>
            <p className="mt-1 font-semibold text-body">{t.recordHint}</p>
          </div>
          <p className="rounded-card bg-white p-8 text-[34px] leading-relaxed font-extrabold text-navy shadow-soft ring-1 ring-line">{passage.text}</p>

          {rec.state === 'blocked' ? (
            <div className="flex items-start gap-3 rounded-card bg-coral-soft p-5 text-coral-ink">
              <MicOff className="mt-0.5 size-6 shrink-0" aria-hidden />
              <div>
                <p className="font-extrabold">{t.micBlocked}</p>
                <p className="mt-1 text-sm font-semibold">{window.basa?.platform === 'win32' ? t.micBlockedFixWin : t.micBlockedFixLinux}</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-6">
              <button
                onClick={toggle}
                className={`flex size-24 shrink-0 cursor-pointer items-center justify-center rounded-full text-white shadow-lift transition ${
                  rec.state === 'recording' ? 'animate-ring bg-coral' : 'bg-blue hover:bg-blue-dark'
                }`}
                aria-label={rec.state === 'recording' ? t.recordStop : t.recordStart}
              >
                {rec.state === 'recording' ? <Square className="size-9 fill-current" /> : <Mic className="size-10" />}
              </button>
              <div className="min-w-0 flex-1">
                <LiveWaveform analyser={rec.analyser} color="#2D5BD3" />
                <div className="mt-2 flex items-center justify-between text-sm">
                  <span className="font-extrabold text-navy tabular-nums">
                    {rec.state === 'recording' ? `● ${elapsed.toFixed(1)} s` : t.recordStart}
                  </span>
                  <span className="flex items-center gap-1.5 font-semibold text-muted">
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
