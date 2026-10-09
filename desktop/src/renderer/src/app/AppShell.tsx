import { NavLink, Outlet } from 'react-router'
import { BookOpen, Mic, Settings, Users } from 'lucide-react'
import { StatusPill } from '@/components/StatusPill'
import { useT } from '@/strings'

export function AppShell() {
  const t = useT()
  const nav = [
    { to: '/', label: t.navClass, icon: Users, end: true },
    { to: '/check', label: t.navCheck, icon: Mic, end: false },
    { to: '/books', label: t.navBooks, icon: BookOpen, end: false },
    { to: '/settings', label: t.navSettings, icon: Settings, end: false }
  ]

  return (
    <div className="flex h-full">
      <aside className="flex w-60 shrink-0 flex-col gap-6 bg-ink px-4 py-6">
        <div className="px-2">
          <p className="font-display text-2xl leading-tight font-bold text-paper">{t.appName}</p>
          <p className="mt-1 text-xs font-bold tracking-widest text-accent-light uppercase">Local AI</p>
        </div>
        <nav className="flex flex-col gap-1">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-bold transition ${
                  isActive ? 'bg-paper text-ink' : 'text-[#c9cfdf] hover:bg-ink-2 hover:text-paper'
                }`
              }
            >
              <Icon className="size-5" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto">
          <StatusPill />
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
