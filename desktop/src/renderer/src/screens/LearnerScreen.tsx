import type { CSSProperties } from 'react'
import type { Progress, WordLabel } from '@/api/types'
import { useQuery } from '@tanstack/react-query'
import { CountUp } from '@/components/CountUp'
import { useNavigate, useParams } from 'react-router'
import { ArrowRight, Mic } from 'lucide-react'
import { api } from '@/api'
import { Art } from '@/components/Art'
import { Emoji } from '@/components/Emoji'
import { Sparkline } from '@/components/Sparkline'
import { Tamaraw } from '@/components/Tamaraw'
import { LevelChip, StatCard } from '@/components/ui'
import { daysSince, useT } from '@/strings'

const INK = '#6B3FA0'

// A loyalty-card style grid of the last 14 days: a violet stamp for every day the child read.
function ReadingCard({ name, days, streak }: { name: string; days: string[]; streak: number }) {
  const t = useT()
  const today = new Date().toISOString().slice(0, 10)
  const cells = Array.from({ length: 14 }, (_, i) => {
    const d = new Date(Date.now() - (13 - i) * 86_400_000)
    const iso = d.toISOString().slice(0, 10)
    return { iso, day: d.getDate(), read: days.includes(iso), today: iso === today }
  })
  return (
    <div className="stagger flex min-h-52 flex-col rounded-card bg-white p-6 shadow-soft ring-1 ring-line" style={{ '--i': 0 } as CSSProperties}>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-xl font-black text-navy">{t.readingCard(name)}</p>
        <p className="text-sm font-bold text-muted">{t.last14}</p>
      </div>
      <p className="mt-1 flex items-center gap-1.5 font-extrabold text-[#5a3290]">
        <Emoji name="fire" size={22} /> {t.readingStreak(streak)}
      </p>
      <div className="mt-4 grid grid-cols-7 gap-x-2 gap-y-3">
        {cells.map((c, i) => (
          <div key={c.iso} className="flex flex-col items-center gap-1">
            <span
              className={`grid size-11 place-items-center rounded-full ${
                c.read ? 'animate-stamp' : c.today ? 'border-2 border-dashed border-[#a58bc9]' : 'bg-side'
              }`}
              style={c.read ? { rotate: `${((i * 37) % 24) - 12}deg`, animationDelay: `${300 + i * 45}ms` } : undefined}
              aria-label={c.read ? `${c.iso}: nagbasa` : c.iso}
            >
              {c.read && (
                <svg viewBox="0 0 44 44" className="size-11" aria-hidden>
                  <circle cx="22" cy="22" r="19" fill="none" stroke={INK} strokeWidth="3" />
                  <polygon points="22,10 25.5,18 34,18.8 27.6,24.4 29.5,32.8 22,28.4 14.5,32.8 16.4,24.4 10,18.8 18.5,18" fill={INK} />
                </svg>
              )}
            </span>
            <span className={`text-xs font-bold ${c.today ? 'text-navy' : 'text-muted'}`}>{c.day}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// The latest two confirmed checks on the same story, side by side, and the words whose result changed.
function ProgressCard({ progress, passageTitle }: { progress?: Progress; passageTitle?: string }) {
  const t = useT()
  const label = (l: WordLabel | null) => (l === null ? '—' : { matched: t.labelMatched, misread: t.labelMisread, skipped: t.labelSkipped }[l])
  const [before, after] = progress?.checks ?? []
  const changed = progress?.words.filter((w) => w.before !== w.after) ?? []
  const change = progress?.wcpm_change ?? null

  return (
    <section className="stagger mt-8 rounded-card bg-white p-6 shadow-soft ring-1 ring-line" style={{ '--i': 5 } as CSSProperties}>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-xl font-extrabold text-navy">{t.progressTitle}</h2>
        {before && passageTitle && <p className="text-sm font-bold text-muted">{t.progressStory(passageTitle)}</p>}
      </div>
      {!before || !after ? (
        <p className="mt-3 font-semibold text-body">{t.progressEmpty}</p>
      ) : (
        <div className="mt-4 grid grid-cols-5 gap-8">
          <div className="col-span-2 flex flex-col gap-3">
            <div className="flex items-center gap-4">
              {[before, after].map((c, i) => (
                <div key={c.assessment_id} className="flex items-center gap-4">
                  {i === 1 && <ArrowRight className="size-6 text-muted" aria-hidden />}
                  <div>
                    <p className="text-sm font-bold text-muted">{t.relDay(daysSince(c.confirmed_at.slice(0, 10)), c.confirmed_at.slice(0, 10))}</p>
                    <p className={`text-[44px] leading-none font-black ${i === 1 ? 'text-navy' : 'text-muted'}`}>{c.wcpm ?? '—'}</p>
                    <p className="text-xs font-bold text-muted">{t.wpm}</p>
                  </div>
                </div>
              ))}
            </div>
            {change !== null && (
              <span
                className={`self-start rounded-full px-3 py-1 text-sm font-extrabold ${
                  change > 0 ? 'bg-teal-soft text-teal-ink' : change < 0 ? 'bg-coral-soft text-coral-ink' : 'bg-side text-navy'
                }`}
              >
                {t.progressDelta(change)}
              </span>
            )}
          </div>
          <div className="col-span-3">
            <p className="text-sm font-extrabold tracking-wider text-muted uppercase">{t.progressWords}</p>
            {changed.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {changed.map((w) => {
                  const better = w.after === 'matched'
                  const worse = w.before === 'matched'
                  return (
                    <span
                      key={w.i}
                      className={`flex flex-col rounded-tile px-3 py-2 ${better ? 'bg-teal-soft text-teal-ink' : worse ? 'bg-coral-soft text-coral-ink' : 'bg-side text-navy'}`}
                    >
                      <span className="text-lg font-black">{w.text}</span>
                      <span className="text-xs font-bold">
                        {label(w.before)} → {label(w.after)}
                      </span>
                    </span>
                  )
                })}
              </div>
            ) : (
              <p className="mt-3 font-semibold text-body">{t.progressNoChange}</p>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

// Mirrors the BOOKR profile: three color-block stat cards, then progress below.
export function LearnerScreen() {
  const t = useT()
  const navigate = useNavigate()
  const { learnerId = '' } = useParams()
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  const { data: stats } = useQuery({ queryKey: ['stats', learnerId], queryFn: () => api.learnerStats(learnerId) })
  const { data: progress } = useQuery({ queryKey: ['progress', learnerId], queryFn: () => api.progress(learnerId) })
  const { data: passages } = useQuery({ queryKey: ['passages'], queryFn: () => api.passages() })
  const learner = learners?.find((l) => l.id === learnerId)
  const history = stats?.wcpm_history ?? []
  const latest = history.at(-1)?.wcpm

  return (
    <div className="w-full max-w-[1680px] px-10 py-10">
      <div className="flex items-center gap-4">
        <h1 className="text-[40px] leading-tight font-black text-navy">{learner?.display_name}</h1>
        <LevelChip level={learner?.level} />
      </div>

      <div className="mt-6 grid grid-cols-[1.5fr_1fr_1fr] gap-6">
        <ReadingCard name={learner?.display_name ?? ''} days={stats?.days_read ?? []} streak={stats?.streak_days ?? 0} />
        <StatCard index={1} color="coral" title={t.statStars} value={<CountUp value={stats?.stars ?? 0} />} emoji="star" />
        <StatCard index={2} color="teal" title={t.statTime} value={<CountUp value={stats?.minutes_read ?? 0} format={t.hm} />} emoji="hourglass" />
      </div>

      <div className="mt-8 grid grid-cols-5 gap-6">
        <section className="stagger col-span-3 rounded-card bg-white p-6 shadow-soft ring-1 ring-line" style={{ '--i': 3 } as CSSProperties}>
          <h2 className="flex items-center gap-2 text-xl font-extrabold text-navy">
            <Emoji name="chart" size={28} /> {t.trendTitle}
          </h2>
          {history.length >= 2 ? (
            <div className="mt-4 flex items-end gap-6">
              <div>
                <p className="text-[56px] leading-none font-black text-navy">
                  <CountUp value={latest ?? 0} />
                </p>
                <p className="mt-2 text-sm font-extrabold text-teal-ink">{t.trendDelta((latest ?? 0) - history[0].wcpm)}</p>
              </div>
              <Sparkline values={history.map((h) => h.wcpm)} width={380} height={110} />
            </div>
          ) : (
            <div className="mt-4 flex items-center gap-4">
              <Tamaraw size={96} />
              <p className="font-semibold text-body">{t.trendEmpty}</p>
            </div>
          )}
        </section>

        <section className="stagger col-span-2 flex flex-col rounded-card bg-white p-6 shadow-soft ring-1 ring-line" style={{ '--i': 4 } as CSSProperties}>
          <h2 className="text-xl font-extrabold text-navy">{t.practicingTitle}</h2>
          <div className="mt-4 flex flex-wrap gap-2">
            {stats?.practicing.length ? (
              stats.practicing.map((w) => (
                <span key={w} className="rounded-full bg-coral-soft px-4 py-2 text-lg font-extrabold text-coral-ink">
                  {w}
                </span>
              ))
            ) : (
              <p className="font-semibold text-body">{t.practicingEmpty}</p>
            )}
          </div>
          <div className="mt-auto flex gap-3 pt-6">
            <button
              onClick={() => navigate(`/check/${learnerId}`)}
              className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-full bg-blue px-4 py-3 text-xl font-extrabold text-white hover:bg-blue-dark"
            >
              <Mic className="size-5" aria-hidden /> {t.classCheck}
            </button>
            <button
              onClick={() => navigate(`/practice/${learnerId}`)}
              className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-full bg-coral px-4 py-3 text-xl font-extrabold text-white hover:brightness-105"
            >
              <Art name="flashcard" size={22} /> {t.classPractice}
            </button>
          </div>
        </section>
      </div>

      <ProgressCard progress={progress} passageTitle={passages?.find((p) => p.id === progress?.checks[0]?.passage_id)?.title} />
    </div>
  )
}
