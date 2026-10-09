import { useState, type CSSProperties } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CountUp } from '@/components/CountUp'
import { useNavigate } from 'react-router'
import { ArrowRight, Mic, Search } from 'lucide-react'
import { api } from '@/api'
import { Art } from '@/components/Art'
import { Emoji } from '@/components/Emoji'
import { Avatar, LevelChip, SampleBadge, StatCard } from '@/components/ui'
import { isDue, nextDue, weekAgo } from '@/lib/due'
import { daysSince, useT } from '@/strings'

type Filter = 'all' | 'practice' | 'due'

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
          {api.mode === 'mock' && <SampleBadge label={t.sampleData} />}
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
