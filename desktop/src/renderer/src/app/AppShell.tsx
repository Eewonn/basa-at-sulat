import { useEffect, useRef, useState } from 'react'
import { Link, Outlet, useLocation, useMatch, useNavigate } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { api } from '@/api'
import { StatusPill } from '@/components/StatusPill'
import { Tamaraw } from '@/components/Tamaraw'
import { Avatar } from '@/components/ui'
import { useT } from '@/strings'

const ITEM = 52 // px height of a nav item
const GAP = 4

// Which nav item a path belongs to (review is part of the Basa flow, book screens of Sulat).
function navIndex(path: string): number {
  if (path.startsWith('/check') || path.startsWith('/review')) return 1
  if (path.startsWith('/books')) return 2
  if (path.startsWith('/settings')) return 3
  return 0
}

// BOOKR-style sidebar: blue header block, overlapping avatar, centered nav, a white pill that slides.
export function AppShell() {
  const t = useT()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const profile = useMatch('/learner/:learnerId')
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  const learnerIndex = learners?.findIndex((l) => l.id === profile?.params.learnerId) ?? -1
  const learner = learnerIndex >= 0 ? learners![learnerIndex] : undefined
  const [cheer, setCheer] = useState<string | null>(null)
  const cheerTimer = useRef<ReturnType<typeof setTimeout>>(undefined)

  const nav = [
    { to: '/', label: t.navClass },
    { to: '/check', label: t.navCheck },
    { to: '/books', label: t.navBooks },
    { to: '/settings', label: t.navSettings }
  ]
  const items = learner ? [{ to: pathname, label: t.navProfile }, ...nav] : nav
  const active = learner ? 0 : navIndex(pathname)

  // A speech bubble belongs to the screen it was shown on.
  useEffect(() => setCheer(null), [pathname])

  const poke = () => {
    clearTimeout(cheerTimer.current)
    setCheer(t.mascotLines[Math.floor(Math.random() * t.mascotLines.length)])
    cheerTimer.current = setTimeout(() => setCheer(null), 2400)
  }

  return (
    <div className="flex h-full">
      <aside className="paper flex w-64 shrink-0 flex-col overflow-y-auto bg-side">
        <div className="relative h-28 shrink-0 bg-blue banig">
          {learner && (
            <button onClick={() => navigate('/')} aria-label={t.back} className="absolute top-5 left-5 cursor-pointer text-white">
              <ArrowLeft className="size-8" strokeWidth={3} />
            </button>
          )}
          <div className="absolute top-12 left-1/2 -translate-x-1/2 rounded-full bg-side p-1.5">
            <div className="rounded-full ring-4 ring-blue">
              {learner ? (
                <Avatar name={learner.display_name} index={learnerIndex} size={112} />
              ) : (
                <button onClick={poke} aria-label={t.mascotName} className="grid size-28 cursor-pointer place-items-center overflow-hidden rounded-full bg-sun-soft">
                  <Tamaraw key={cheer ?? 'idle'} mood={cheer ? 'happy' : 'idle'} size={103} />
                </button>
              )}
            </div>
          </div>
        </div>
        <div className="relative mt-20 text-center">
          {cheer ? (
            <p key={cheer} className="mx-4 animate-pop rounded-tile bg-white px-3 py-2 font-hand text-2xl text-navy shadow-soft">
              {cheer}
            </p>
          ) : (
            <>
              <p className="text-2xl font-black text-navy">{learner ? learner.display_name : t.appName}</p>
              <p className="text-xs font-extrabold tracking-widest text-blue uppercase">{learner ? `Grade ${learner.grade}` : 'Local AI'}</p>
            </>
          )}
        </div>
        <nav className="relative mt-8 flex flex-col pl-6" style={{ gap: GAP }}>
          <span
            aria-hidden
            className="absolute right-0 left-6 rounded-l-full bg-white shadow-soft transition-[top] duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
            style={{ top: active * (ITEM + GAP), height: ITEM }}
          />
          {items.map(({ to, label }, i) => (
            <Link
              key={`${label}-${to}`}
              to={to}
              aria-current={i === active ? 'page' : undefined}
              className={`relative grid place-items-center rounded-l-full text-lg font-extrabold transition-colors ${
                i === active ? 'text-navy' : 'text-blue hover:text-blue-dark'
              }`}
              style={{ height: ITEM }}
            >
              {label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto p-4">
          <StatusPill />
        </div>
      </aside>
      <main className="paper min-w-0 flex-1 overflow-y-auto bg-page">
        <div key={pathname} className="h-full animate-page-in">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
