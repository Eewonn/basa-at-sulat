import { createContext, useCallback, useContext, useState, type CSSProperties, type ReactNode } from 'react'
import { CheckCircle2 } from 'lucide-react'
import type { Level } from '@/api/types'
import { useT } from '@/strings'
import { Emoji, type EmojiName } from './Emoji'
import { Tamaraw } from './Tamaraw'

const LEVEL_STYLE: Record<Level, string> = {
  'Low Emerging': 'bg-coral-soft text-coral-ink',
  'High Emerging': 'bg-[#ffe9d6] text-[#9a4a00]',
  Developing: 'bg-sun-soft text-[#7a5a00]',
  Transitioning: 'bg-blue-soft text-blue-dark',
  'At Grade Level': 'bg-teal-soft text-teal-ink'
}

// Level is always written out, never color alone, and marked as an estimate (it isn't an official CRLA result).
export function LevelChip({ level, onDark = false }: { level?: Level | null; onDark?: boolean }) {
  const t = useT()
  if (!level) return null
  return (
    <span
      title={t.levelEstNote}
      className={`inline-flex items-baseline gap-1.5 self-start rounded-full px-3 py-1 text-sm font-extrabold ${
        onDark ? 'bg-white text-navy' : LEVEL_STYLE[level] ?? 'bg-side text-navy'
      }`}
    >
      <span className="text-xs font-bold">{t.levelEst}</span>
      {level}
    </span>
  )
}

export function SampleBadge({ label }: { label: string }) {
  return <span className="sample-badge rounded-full bg-side px-3 py-1 text-xs font-bold text-muted">{label}</span>
}

const AVATAR_COLORS = ['bg-blue', 'bg-coral', 'bg-teal', 'bg-purple']

// Initial in a colored circle (white text only at large bold sizes), or the mascot.
export function Avatar({ name, index = 0, size = 56, mascot = false }: { name: string; index?: number; size?: number; mascot?: boolean }) {
  return (
    <span
      className={`grid shrink-0 place-items-center overflow-hidden rounded-full font-black text-white ${
        mascot ? 'bg-sun-soft' : AVATAR_COLORS[index % AVATAR_COLORS.length]
      }`}
      style={{ width: size, height: size, fontSize: Math.max(22, size * 0.42) }}
      aria-hidden
    >
      {mascot ? <Tamaraw size={size * 0.92} /> : name[0]}
    </span>
  )
}

// BOOKR-style color block: title, big value, illustration.
export function StatCard({
  title,
  value,
  emoji,
  color,
  compact = false,
  index = 0
}: {
  title: string
  value: ReactNode
  emoji: EmojiName
  color: 'coral' | 'blue' | 'teal' | 'purple'
  compact?: boolean
  index?: number
}) {
  const bg = { coral: 'bg-coral', blue: 'bg-blue', teal: 'bg-teal', purple: 'bg-purple' }[color]
  return (
    <div
      className={`group stagger relative flex flex-col overflow-hidden rounded-card text-white shadow-soft ${bg} ${compact ? 'min-h-36 p-5' : 'min-h-52 p-6'}`}
      style={{ '--i': index } as CSSProperties}
    >
      <p className={`font-extrabold ${compact ? 'pr-16 text-lg leading-snug' : 'text-xl'}`}>{title}</p>
      <p className="mt-1 text-[40px] leading-tight font-black">{value}</p>
      <Emoji name={emoji} size={compact ? 72 : 104} className={`absolute drop-shadow-md transition-transform duration-300 group-hover:-rotate-8 group-hover:scale-115 ${compact ? 'right-4 bottom-3' : 'right-5 bottom-4'}`} />
    </div>
  )
}

export function CategoryTile({ label, emoji, selected, onClick }: { label: string; emoji: EmojiName; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className="group flex w-24 cursor-pointer flex-col items-center gap-2" aria-pressed={selected}>
      <span
        className={`grid size-24 place-items-center rounded-tile transition group-hover:-translate-y-1 ${
          selected ? 'bg-white ring-4 ring-blue shadow-soft' : 'bg-blue-soft'
        }`}
      >
        <Emoji name={emoji} size={56} />
      </span>
      <span className={`text-[15px] font-extrabold ${selected ? 'text-blue' : 'text-navy'}`}>{label}</span>
    </button>
  )
}

const ToastContext = createContext<(msg: string) => void>(() => {})

export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState<string | null>(null)
  const show = useCallback((m: string) => {
    setMsg(m)
    setTimeout(() => setMsg(null), 3200)
  }, [])
  return (
    <ToastContext.Provider value={show}>
      {children}
      {msg && (
        <div role="status" className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 animate-pop items-center gap-2 rounded-full bg-navy px-5 py-3 font-bold text-white shadow-lift">
          <CheckCircle2 className="size-5 text-[#7fe0cf]" aria-hidden />
          {msg}
        </div>
      )}
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
