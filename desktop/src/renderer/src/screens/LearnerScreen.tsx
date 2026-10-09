import type { CSSProperties } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CountUp } from '@/components/CountUp'
import { useNavigate, useParams } from 'react-router'
import { Mic} from 'lucide-react'
import { api } from '@/api'
import { Art } from '@/components/Art'
import { Emoji } from '@/components/Emoji'
import { Sparkline } from '@/components/Sparkline'
import { Tamaraw } from '@/components/Tamaraw'
import { LevelChip, StatCard } from '@/components/ui'
import { useT } from '@/strings'

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

// Mirrors the BOOKR profile: three color-block stat cards, then progress below.
export function LearnerScreen() {
  const t = useT()
  const navigate = useNavigate()
  const { learnerId = '' } = useParams()
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  const { data: stats } = useQuery({ queryKey: ['stats', learnerId], queryFn: () => api.learnerStats(learnerId) })
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
    </div>
  )
}
