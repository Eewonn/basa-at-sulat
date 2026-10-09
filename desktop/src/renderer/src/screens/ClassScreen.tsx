import { useState, type CSSProperties } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CountUp } from '@/components/CountUp'
import { useNavigate } from 'react-router'
import { ArrowRight, BookPlus, Download, Mic, RefreshCw, Search } from 'lucide-react'
import { api } from '@/api'
import type { Learner } from '@/api/types'
import { Art } from '@/components/Art'
import { Emoji } from '@/components/Emoji'
import { PlanView } from '@/components/PlanView'
import { Avatar, LevelChip, StatCard } from '@/components/ui'
import { isDue, nextDue, weekAgo } from '@/lib/due'
import { daysSince, useT } from '@/strings'

type Filter = 'all' | 'practice' | 'due'

// The window may not navigate to the engine, so the file is fetched and saved from a blob: URL.
async function exportCsv() {
  const url = URL.createObjectURL(await api.exportCsv())
  const a = document.createElement('a')
  a.href = url
  a.download = 'basa-results.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export function ClassScreen() {
  const t = useT()
  const navigate = useNavigate()
  const { data: learners, isLoading } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  const { data: cls } = useQuery({ queryKey: ['classSettings'], queryFn: () => api.classSettings() })

  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const since = weekAgo()
  const checked = learners?.filter((l) => !isDue(l, since)).length ?? 0
  const next = learners && nextDue(learners)
  const shown = learners
    ?.map((l, i) => ({ l, i }))
    .filter(({ l }) => l.display_name.toLowerCase().includes(query.trim().toLowerCase()))
    .filter(({ l }) => (filter === 'practice' ? l.needs_practice : filter === 'due' ? isDue(l, since) : true))
  const needPractice = learners?.filter((l) => l.needs_practice).length ?? 0
  const stars = learners?.reduce((sum, l) => sum + (l.stars ?? 0), 0) ?? 0
  const wcpms = learners?.flatMap((l) => (l.latest_wcpm === undefined ? [] : [l.latest_wcpm])) ?? []
  const avgWcpm = wcpms.length ? Math.round(wcpms.reduce((a, b) => a + b, 0) / wcpms.length) : 0

  return (
    <div className="w-full max-w-[1680px] px-10 py-10">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-hand text-[28px] leading-tight text-coral-ink">{t.greeting(new Date().getHours(), cls?.teacher_name || undefined)}</p>
          <h1 className="text-[40px] leading-tight font-black text-navy">{t.classTitle}</h1>
          <p className="mt-1 font-semibold text-body">
            {cls && learners ? t.classLine(cls.grade, cls.section, learners.length) : '\u00a0'}
          </p>
        </div>
        <div className="flex flex-col items-end gap-3">
          <div className="flex items-center gap-3">
            <button onClick={() => void exportCsv()} className="flex cursor-pointer items-center gap-2 rounded-full px-4 py-2 font-extrabold text-blue ring-2 ring-blue-soft transition hover:bg-blue-soft">
              <Download className="size-4" aria-hidden /> {t.exportCsv}
            </button>
          </div>
          {next && (
            <button
              onClick={() => navigate(`/check/${next.id}`)}
              className="flex cursor-pointer items-center gap-2 rounded-full bg-blue py-3 pr-5 pl-6 text-lg font-extrabold text-white shadow-soft transition hover:bg-blue-dark"
            >
              <Mic className="size-5" aria-hidden /> {t.nextReader(next.display_name)} <ArrowRight className="size-5" aria-hidden />
            </button>
          )}
        </div>
      </header>

      {learners && (
        <div className="mt-6 grid grid-cols-2 gap-5 xl:grid-cols-4">
          <StatCard compact index={0} color="blue" title={t.sumChecked} value={<><CountUp value={checked} />/{learners.length}</>} emoji="microphone" />
          <StatCard compact index={1} color="coral" title={t.sumPractice} value={<CountUp value={needPractice} />} emoji="books" />
          <StatCard compact index={2} color="teal" title={t.sumWcpm} value={<CountUp value={avgWcpm} />} emoji="chart" />
          <StatCard compact index={3} color="purple" title={t.sumStars} value={<CountUp value={stars} />} emoji="star" />
        </div>
      )}

      {learners && <Groups learners={learners} />}

      <div className="mt-8 flex flex-wrap items-center gap-3">
        <label className="flex w-72 items-center gap-2 rounded-full bg-white px-4 py-2.5 ring-2 ring-line focus-within:ring-blue">
          <Search className="size-5 text-muted" aria-hidden />
          <input className="w-full bg-transparent font-bold text-navy outline-none" placeholder={t.searchLearner} aria-label={t.searchLearner} value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
        {(
          [
            ['all', t.filterAll],
            ['practice', t.classNeedsPractice],
            ['due', t.filterDue]
          ] as [Filter, string][]
        ).map(([f, label]) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            aria-pressed={filter === f}
            className={`cursor-pointer rounded-full px-4 py-2.5 font-extrabold transition ${filter === f ? 'bg-navy text-white' : 'bg-side text-navy hover:bg-blue-soft'}`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-6">
        {isLoading && Array.from({ length: 6 }, (_, i) => <div key={i} className="shimmer h-60 rounded-card" />)}
        {shown?.length === 0 && <p className="font-bold text-muted">{t.noMatch}</p>}
        {shown?.map(({ l, i }) => (
          <article key={l.id} style={{ '--i': i + 4 } as CSSProperties} className="stagger flex flex-col gap-4 rounded-card bg-white p-5 shadow-soft ring-1 ring-line transition hover:-translate-y-1 hover:shadow-lift">
            <button onClick={() => navigate(`/learner/${l.id}`)} className="flex cursor-pointer items-center gap-4 text-left">
              <Avatar name={l.display_name} index={i} size={64} />
              <div className="min-w-0 flex-1">
                <p className="text-2xl font-black text-navy">{l.display_name}</p>
                <p className="text-sm font-semibold text-muted">
                  {l.last_check ? `${t.classLastCheck}: ${t.relDay(daysSince(l.last_check), l.last_check)}` : t.classNeverChecked}
                </p>
              </div>
            </button>
            <div className="flex flex-wrap items-center gap-2">
              <LevelChip level={l.level} />
              {l.needs_practice && (
                <span className="rounded-full bg-coral-soft px-3 py-1 text-sm font-extrabold text-coral-ink">{t.classNeedsPractice}</span>
              )}
            </div>
            <div className="flex gap-4 text-sm font-extrabold text-navy">
              <span className="flex items-center gap-1.5">
                <Emoji name="star" size={22} /> {l.stars ?? 0}
              </span>
              <span className="flex items-center gap-1.5">
                <Emoji name="fire" size={22} /> {t.days(l.streak_days ?? 0)}
              </span>
            </div>
            <div className="mt-auto flex gap-2">
              <button
                onClick={() => navigate(`/check/${l.id}`)}
                className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-full bg-blue px-4 py-3 font-extrabold text-white transition hover:bg-blue-dark"
              >
                <Mic className="size-5" aria-hidden /> {t.classCheck}
              </button>
              <button
                onClick={() => navigate(`/practice/${l.id}`)}
                className="flex cursor-pointer items-center justify-center gap-2 rounded-full px-4 py-3 font-extrabold text-coral-ink ring-2 ring-coral transition hover:bg-coral-soft"
              >
                <Art name="flashcard" size={22} /> {t.classPractice}
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}

// GET /class: who reads at the same level, the words they share, and a draft plan for the group.
// The first load can take ~25 s (the plan's example sentence comes from the local model), later loads are cached.
function Groups({ learners }: { learners: Learner[] }) {
  const t = useT()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: groups, isLoading, isError } = useQuery({ queryKey: ['class'], queryFn: () => api.classGroups(), retry: false })
  // A new example sentence means running the model again, so this is as slow as a first load.
  const remake = useMutation({ mutationFn: () => api.classGroups(true), onSuccess: (fresh) => qc.setQueryData(['class'], fresh) })
  const index = new Map(learners.map((l, i) => [l.id, { l, i }]))

  return (
    <section className="mt-8">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-extrabold text-navy">{t.groupsTitle}</h2>
        {groups && groups.some((g) => g.draft_plan) && (
          <button
            disabled={remake.isPending}
            onClick={() => remake.mutate()}
            className="flex cursor-pointer items-center gap-2 rounded-full px-4 py-2 font-extrabold text-blue ring-2 ring-blue-soft transition hover:bg-blue-soft disabled:cursor-wait disabled:opacity-60"
          >
            <RefreshCw className={`size-4 ${remake.isPending ? 'animate-spin' : ''}`} aria-hidden /> {t.groupRefresh}
          </button>
        )}
      </div>
      {isLoading && <p className="shimmer mt-3 rounded-card p-5 font-bold text-body">{t.groupsLoading}</p>}
      {isError && <p className="mt-3 rounded-card bg-coral-soft p-5 font-bold text-coral-ink">{t.groupsFailed}</p>}
      {groups?.length === 0 && <p className="mt-3 rounded-card bg-side p-5 font-bold text-body">{t.groupsEmpty}</p>}
      <div className="mt-3 grid grid-cols-[repeat(auto-fill,minmax(360px,1fr))] items-start gap-5">
        {groups?.map((g, n) => (
          <article key={g.level} style={{ '--i': n + 4 } as CSSProperties} className="stagger flex flex-col gap-3 rounded-card bg-white p-5 shadow-soft ring-1 ring-line">
            <div className="flex items-center justify-between gap-3">
              <LevelChip level={g.level} />
              <div className="flex -space-x-2">
                {g.learner_ids.map((id) => {
                  const m = index.get(id)
                  return m && <Avatar key={id} name={m.l.display_name} index={m.i} size={36} />
                })}
              </div>
            </div>
            <p className="text-sm font-bold text-muted">{g.learner_ids.map((id) => index.get(id)?.l.display_name ?? id).join(', ')}</p>
            <div>
              <p className="text-sm font-extrabold text-navy">{t.groupWords}</p>
              {g.common_missed_words.length ? (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {g.common_missed_words.map((w) => (
                    <span key={w} className="rounded-full bg-coral-soft px-3 py-1 font-extrabold text-coral-ink">{w}</span>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-sm font-semibold text-body">{t.groupNoWords}</p>
              )}
            </div>
            {g.draft_plan ? (
              <details className="group rounded-tile bg-banig-soft p-3">
                <summary className="cursor-pointer font-extrabold text-navy">{t.groupPlan}</summary>
                <PlanView plan={g.draft_plan} />
              </details>
            ) : (
              <p className="text-sm font-semibold text-muted">{t.groupNoPlan}</p>
            )}
            {g.common_missed_words.length > 0 && (
              <button
                onClick={() => navigate('/books/new', { state: { words: g.common_missed_words } })}
                className="flex cursor-pointer items-center justify-center gap-2 rounded-full bg-purple px-5 py-3 font-black text-white shadow-soft transition hover:-translate-y-0.5"
              >
                <BookPlus className="size-5" aria-hidden /> {t.groupMakeBook}
              </button>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
