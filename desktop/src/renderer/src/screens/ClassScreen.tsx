import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { Mic, Sparkles } from 'lucide-react'
import { api } from '@/api'
import { LevelChip, SampleBadge } from '@/components/ui'
import { useT } from '@/strings'

export function ClassScreen() {
  const t = useT()
  const navigate = useNavigate()
  const { data: learners, isLoading } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })

  return (
    <div className="mx-auto max-w-6xl px-10 py-10">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="font-display text-4xl font-bold text-ink">{t.classTitle}</h1>
          <p className="mt-1 text-body">{t.classSubtitle}</p>
        </div>
        {api.mode === 'mock' && <SampleBadge label={t.sampleData} />}
      </header>

      <div className="mt-8 grid grid-cols-3 gap-5">
        {isLoading &&
          Array.from({ length: 6 }, (_, i) => <div key={i} className="h-44 animate-pulse rounded-card bg-paper-2" />)}
        {learners?.map((l) => (
          <article key={l.id} className="flex flex-col gap-3 rounded-card bg-card p-5 ring-1 ring-line">
            <div className="flex items-center gap-3">
              <span className="grid size-12 place-items-center rounded-full bg-paper-2 font-display text-xl font-bold text-ink">
                {l.display_name[0]}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-display text-xl font-bold text-ink">{l.display_name}</p>
                <p className="text-sm text-muted">
                  {l.last_check ? `${t.classLastCheck}: ${l.last_check}` : t.classNeverChecked}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <LevelChip level={l.level} />
              {l.needs_practice && (
                <span className="rounded-full bg-accent-bg px-3 py-1 text-xs font-extrabold text-[#8a3d12]">{t.classNeedsPractice}</span>
              )}
            </div>
            <div className="mt-auto flex gap-2">
              <button
                onClick={() => navigate(`/check/${l.id}`)}
                className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl bg-ink px-4 py-2.5 font-bold text-paper transition hover:bg-ink-2"
              >
                <Mic className="size-4" aria-hidden /> {t.classCheck}
              </button>
              <button
                onClick={() => navigate(`/practice/${l.id}`)}
                className="flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-paper-2 px-4 py-2.5 font-bold text-ink ring-1 ring-line transition hover:bg-line"
              >
                <Sparkles className="size-4" aria-hidden /> {t.classPractice}
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
