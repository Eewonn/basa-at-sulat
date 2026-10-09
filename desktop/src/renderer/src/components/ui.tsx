import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { Emoji, type EmojiName } from './Emoji'
import { Tamaraw } from './Tamaraw'

const LEVEL_STYLE: Record<string, string> = {
  Emerging: 'bg-coral-soft text-coral-ink',
  Developing: 'bg-sun-soft text-[#7a5a00]',
  Transitioning: 'bg-blue-soft text-blue-dark',
  'Grade level': 'bg-teal-soft text-teal-ink'
}

// Level is always written out, never color alone.
export function LevelChip({ level, onDark = false }: { level?: string; onDark?: boolean }) {
  if (!level) return null
  return (
    <span
      className={`inline-flex self-start rounded-full px-3 py-1 text-sm font-extrabold ${
        onDark ? 'bg-white text-navy' : LEVEL_STYLE[level] ?? 'bg-side text-navy'
      }`}
    >
      {level}
    </span>
  )
}

export function SampleBadge({ label }: { label: string }) {
  return <span className="rounded-full bg-side px-3 py-1 text-xs font-bold text-muted">{label}</span>
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
export function StatCard({ title, value, emoji, color }: { title: string; value: string; emoji: EmojiName; color: 'coral' | 'blue' | 'teal' }) {
  const bg = { coral: 'bg-coral', blue: 'bg-blue', teal: 'bg-teal' }[color]
  return (
    <div className={`relative flex h-52 flex-col overflow-hidden rounded-card p-6 text-white shadow-soft banig ${bg}`}>
      <p className="text-xl font-extrabold">{title}</p>
      <p className="mt-1 text-[40px] leading-tight font-black">{value}</p>
      <Emoji name={emoji} size={104} className="absolute right-5 bottom-4 drop-shadow-md" />
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
