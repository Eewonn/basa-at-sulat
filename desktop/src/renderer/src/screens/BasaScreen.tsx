import type { CSSProperties } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { Mic } from 'lucide-react'
import { api } from '@/api'
import { Tamaraw } from '@/components/Tamaraw'
import { Avatar, LevelChip } from '@/components/ui'
import { useT } from '@/strings'

// The Basa tab: who still needs a check this week, and what was checked recently.
export function BasaScreen() {
  const t = useT()
  const navigate = useNavigate()
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  const { data: recent } = useQuery({ queryKey: ['recent'], queryFn: () => api.recentChecks() })

  const weekAgo = new Date(Date.now() - 7 * 86_400_000).toISOString().slice(0, 10)
  const today = new Date().toISOString().slice(0, 10)
  const indexed = learners?.map((l, i) => ({ l, i })) ?? []
  const due = indexed.filter(({ l }) => !l.last_check || l.last_check < weekAgo)
  const done = indexed.filter(({ l }) => l.last_check && l.last_check >= weekAgo)

  return (
    <div className="flex w-full max-w-[1680px] gap-8 px-10 py-10">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-5">
          <Tamaraw size={96} />
          <div>
            <p className="text-lg font-extrabold text-coral-ink">{t.basaEyebrow}</p>
            <h1 className="text-[40px] leading-tight font-black text-navy">{t.navCheck}</h1>
          </div>
        </div>

        <h2 className="mt-8 text-xl font-extrabold text-navy">
          {t.dueTitle} <span className="text-coral-ink">({due.length})</span>
        </h2>
        {due.length === 0 ? (
          <p className="mt-3 rounded-card bg-teal-soft p-5 font-bold text-teal-ink">{t.dueEmpty}</p>
        ) : (
          <div className="mt-3 grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-5">
            {due.map(({ l, i }, n) => (
              <article key={l.id} style={{ '--i': n } as CSSProperties} className="stagger flex flex-col gap-4 rounded-card bg-white p-5 shadow-soft ring-2 ring-coral-soft">
                <div className="flex items-center gap-4">
                  <Avatar name={l.display_name} index={i} size={64} />
                  <div className="min-w-0 flex-1">
                    <p className="text-2xl font-black text-navy">{l.display_name}</p>
                    <p className="text-sm font-semibold text-muted">
                      {l.last_check ? `${t.classLastCheck}: ${l.last_check}` : t.classNeverChecked}
                    </p>
                  </div>
                </div>
                <LevelChip level={l.level} />
                <button
                  onClick={() => navigate(`/check/${l.id}`)}
                  className="mt-auto flex cursor-pointer items-center justify-center gap-2 rounded-full bg-blue px-4 py-3 text-lg font-extrabold text-white transition hover:bg-blue-dark"
                >
                  <Mic className="size-5" aria-hidden /> {t.classCheck}
                </button>
              </article>
            ))}
          </div>
        )}

        <h2 className="mt-10 text-xl font-extrabold text-navy">
          {t.doneTitle} <span className="text-teal-ink">({done.length})</span>
        </h2>
        <div className="mt-3 grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
          {done.map(({ l, i }, n) => (
            <button
              key={l.id}
              style={{ '--i': due.length + n } as CSSProperties}
              onClick={() => navigate(`/check/${l.id}`)}
              className="stagger flex cursor-pointer items-center gap-3 rounded-card bg-white p-4 text-left shadow-soft ring-1 ring-line transition hover:-translate-y-1"
            >
              <Avatar name={l.display_name} index={i} size={44} />
              <div className="min-w-0">
                <p className="text-lg font-black text-navy">{l.display_name}</p>
                <p className="text-xs font-semibold text-muted">{l.last_check}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      <aside className="w-80 shrink-0 space-y-5">
        <section className="stagger rounded-card bg-white p-5 shadow-soft ring-1 ring-line" style={{ '--i': 2 } as CSSProperties}>
          <h2 className="text-lg font-extrabold text-navy">{t.recentTitle}</h2>
          <ul className="mt-3 divide-y divide-line">
            {recent?.map((r) => (
              <li key={r.assessment_id} className="flex items-center gap-3 py-3">
                <div className="min-w-0 flex-1">
                  <p className="font-extrabold text-navy">{r.display_name}</p>
                  <p className="truncate text-sm font-semibold text-muted">
                    {r.date === today ? t.today : r.date} · {r.passage_title}
                  </p>
                </div>
                <span className="rounded-full bg-blue-soft px-3 py-1 text-sm font-black text-blue-dark tabular-nums">
                  {r.wcpm} {t.wpm}
                </span>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-card bg-sun-soft p-5">
          <p className="text-sm font-black tracking-widest text-[#6b4f00] uppercase">{t.tipTitle}</p>
          <p className="mt-1 font-bold text-navy">{t.tipText}</p>
        </section>
      </aside>
    </div>
  )
}
