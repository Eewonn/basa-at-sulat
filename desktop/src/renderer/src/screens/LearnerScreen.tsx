import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { Mic, Sparkles } from 'lucide-react'
import { api } from '@/api'
import { Emoji } from '@/components/Emoji'
import { Sparkline } from '@/components/Sparkline'
import { Tamaraw } from '@/components/Tamaraw'
import { LevelChip, StatCard } from '@/components/ui'
import { useT } from '@/strings'

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

      <div className="mt-6 grid grid-cols-3 gap-6">
        <StatCard color="coral" title={t.statStars} value={String(stats?.stars ?? 0)} emoji="star" />
        <StatCard color="blue" title={t.statStreak} value={t.days(stats?.streak_days ?? 0)} emoji="fire" />
        <StatCard color="teal" title={t.statTime} value={t.hm(stats?.minutes_read ?? 0)} emoji="hourglass" />
      </div>

      <div className="mt-8 grid grid-cols-5 gap-6">
        <section className="col-span-3 rounded-card bg-white p-6 shadow-soft ring-1 ring-line">
          <h2 className="flex items-center gap-2 text-xl font-extrabold text-navy">
            <Emoji name="chart" size={28} /> {t.trendTitle}
          </h2>
          {history.length >= 2 ? (
            <div className="mt-4 flex items-end gap-6">
              <div>
                <p className="text-[56px] leading-none font-black text-navy tabular-nums">{latest}</p>
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

        <section className="col-span-2 flex flex-col rounded-card bg-white p-6 shadow-soft ring-1 ring-line">
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
              <Sparkles className="size-5" aria-hidden /> {t.classPractice}
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
