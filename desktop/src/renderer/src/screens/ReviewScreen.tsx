import { Fragment, useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { Cpu, Lock, Pause, RotateCcw, Sparkles } from 'lucide-react'
import { api } from '@/api'
import type { Assessment, Learner, WordLabel } from '@/api/types'
import { Tamaraw } from '@/components/Tamaraw'
import { WordChip } from '@/components/WordChip'
import { LevelChip, useToast } from '@/components/ui'
import { useT } from '@/strings'

export function ReviewScreen() {
  const t = useT()
  const toast = useToast()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { assessmentId = '' } = useParams()
  const { data: a } = useQuery<Assessment>({
    queryKey: ['assessment', assessmentId],
    queryFn: () => Promise.reject(new Error('No assessment in cache')),
    staleTime: Infinity,
    retry: false
  })
  const learner = qc.getQueryData<Learner[]>(['learners'])?.find((l) => l.id === a?.learner_id)
  const [confirmed, setConfirmed] = useState(false)

  const save = (next: Assessment) => qc.setQueryData(['assessment', assessmentId], next)
  const fix = useMutation({
    mutationFn: ({ i, label }: { i: number; label: WordLabel }) => api.overrideWord(assessmentId, i, label),
    onSuccess: save
  })
  const confirm = useMutation({
    mutationFn: () => api.confirm(assessmentId),
    onSuccess: (next) => {
      save(next)
      setConfirmed(true)
      qc.invalidateQueries({ queryKey: ['stats', next.learner_id] })
      toast(t.savedToast)
    }
  })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !confirmed && !confirm.isPending) confirm.mutate()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  if (!a) return null
  const flagged = a.words.filter((w) => w.label !== 'matched').length
  const seconds = a.timings ? ((a.timings.convert_ms + a.timings.align_ms + a.timings.score_ms) / 1000).toFixed(1) : null

  return (
    <div className="flex h-full">
      <section className="min-w-0 flex-1 overflow-y-auto px-10 py-10">
        <p className="text-sm font-black tracking-widest text-coral-ink uppercase">{learner?.display_name}</p>
        <h1 className="mt-1 text-[40px] leading-tight font-black text-navy">{t.reviewTitle}</h1>
        <div className="mt-6 flex flex-wrap items-start gap-x-1 gap-y-3 rounded-card bg-white p-6 shadow-soft ring-1 ring-line">
          {a.words.map((w) => {
            const pause = a.pauses.find((p) => p.before_word === w.i)
            return (
              <Fragment key={w.i}>
                {pause && (
                  <span
                    className="mt-3 flex animate-word-in items-center gap-1 rounded-full bg-sun-soft px-3 py-1 text-xs font-black text-navy"
                    style={{ animationDelay: `${w.i * 40}ms` }}
                  >
                    <Pause className="size-3.5" aria-hidden />
                    {t.pause} {pause.seconds.toFixed(1)} s
                  </span>
                )}
                <WordChip word={w} delayMs={w.i * 40} onFix={(label) => fix.mutate({ i: w.i, label })} />
              </Fragment>
            )
          })}
        </div>
      </section>

      <aside className="flex w-80 shrink-0 flex-col gap-4 bg-side px-6 py-10">
        <div className="flex flex-col gap-2 rounded-card bg-blue p-6 text-white shadow-soft banig">
          <p className="text-[64px] leading-none font-black tabular-nums">{a.wcpm}</p>
          <p className="text-sm font-bold">{t.wcpmLabel}</p>
          <LevelChip level={a.level} onDark />
        </div>
        <p className={`rounded-tile px-4 py-3 font-extrabold ${flagged ? 'bg-coral-soft text-coral-ink' : 'bg-teal-soft text-teal-ink'}`}>
          {flagged ? t.needsCheck(flagged) : t.allClear}
        </p>
        <div className="space-y-2 text-sm font-semibold text-body">
          {seconds && (
            <p className="flex items-start gap-2">
              <Cpu className="mt-0.5 size-4 shrink-0 text-teal-ink" aria-hidden /> {t.scoredIn(seconds)}
            </p>
          )}
          <p className="flex items-start gap-2">
            <Lock className="mt-0.5 size-4 shrink-0 text-teal-ink" aria-hidden /> {t.nothingLeaves}
          </p>
        </div>
        <div className="mt-auto flex flex-col gap-2">
          {confirmed ? (
            <>
              <div className="flex justify-center">
                <Tamaraw mood="happy" size={110} />
              </div>
              <button
                onClick={() => navigate(`/practice/${a.learner_id}`)}
                className="flex animate-pop cursor-pointer items-center justify-center gap-2 rounded-full bg-coral px-4 py-4 text-xl font-black text-white shadow-soft transition hover:brightness-105"
              >
                <Sparkles className="size-5" aria-hidden /> {t.startPractice(learner?.display_name ?? '')}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => confirm.mutate()}
                disabled={confirm.isPending}
                className="cursor-pointer rounded-full bg-teal px-4 py-4 text-xl font-black text-white shadow-soft transition hover:brightness-105 disabled:opacity-60"
              >
                {t.confirm} <span className="ml-1 opacity-80">↵</span>
              </button>
              <button
                onClick={() => navigate(`/check/${a.learner_id}`)}
                className="flex cursor-pointer items-center justify-center gap-2 rounded-full px-4 py-3 font-extrabold text-navy ring-2 ring-navy transition hover:bg-white"
              >
                <RotateCcw className="size-4" aria-hidden /> {t.reRecord}
              </button>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}
