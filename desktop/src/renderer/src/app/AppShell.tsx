import { NavLink, Outlet, useMatch, useNavigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { api } from '@/api'
import { StatusPill } from '@/components/StatusPill'
import { Avatar } from '@/components/ui'
import { useT } from '@/strings'

// BOOKR-style sidebar: blue header block, overlapping avatar, centered nav, white active pill.
export function AppShell() {
  const t = useT()
  const navigate = useNavigate()
  const profile = useMatch('/learner/:learnerId')
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  const learnerIndex = learners?.findIndex((l) => l.id === profile?.params.learnerId) ?? -1
  const learner = learnerIndex >= 0 ? learners![learnerIndex] : undefined

  const nav = [
    { to: '/', label: t.navClass, end: true },
    { to: '/check', label: t.navCheck, end: false },
    { to: '/books', label: t.navBooks, end: false },
    { to: '/settings', label: t.navSettings, end: false }
  ]

  return (
    <div className="flex h-full">
      <aside className="flex w-64 shrink-0 flex-col overflow-y-auto bg-side">
        <div className="relative h-28 shrink-0 bg-blue banig">
          {learner && (
            <button onClick={() => navigate('/')} aria-label={t.back} className="absolute top-5 left-5 cursor-pointer text-white">
              <ArrowLeft className="size-8" strokeWidth={3} />
            </button>
          )}
          <div className="absolute top-12 left-1/2 -translate-x-1/2 rounded-full bg-side p-1.5">
            <div className="rounded-full ring-4 ring-blue">
              {learner ? <Avatar name={learner.display_name} index={learnerIndex} size={112} /> : <Avatar name="" mascot size={112} />}
            </div>
          </div>
        </div>
        <div className="mt-20 text-center">
          <p className="text-2xl font-black text-navy">{learner ? learner.display_name : t.appName}</p>
          <p className="text-xs font-extrabold tracking-widest text-blue uppercase">{learner ? `Grade ${learner.grade}` : 'Local AI'}</p>
        </div>
        <nav className="mt-8 flex flex-col gap-1 pl-6">
          {learner && (
            <span className="rounded-l-full bg-white py-3 text-center text-lg font-extrabold text-navy">{t.navProfile}</span>
          )}
          {nav.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `rounded-l-full py-3 text-center text-lg font-extrabold transition ${
                  isActive && !learner ? 'bg-white text-navy' : 'text-blue hover:text-blue-dark'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto p-4">
          <StatusPill />
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto bg-page">
        <Outlet />
      </main>
    </div>
  )
}
