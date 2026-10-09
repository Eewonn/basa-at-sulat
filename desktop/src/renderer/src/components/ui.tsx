import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { CheckCircle2 } from 'lucide-react'

const LEVEL_STYLE: Record<string, string> = {
  Emerging: 'bg-accent-bg text-[#8a3d12]',
  Developing: 'bg-[#f6e7c8] text-[#6b4a0c]',
  Transitioning: 'bg-[#dfe6f5] text-ink',
  'Grade level': 'bg-correct-bg text-[#14504d]'
}

// Level is always written out, never color alone.
export function LevelChip({ level }: { level?: string }) {
  if (!level) return null
  return (
    <span className={`inline-flex self-start rounded-full px-3 py-1 text-xs font-extrabold ${LEVEL_STYLE[level] ?? 'bg-paper-2 text-ink'}`}>
      {level}
    </span>
  )
}

export function SampleBadge({ label }: { label: string }) {
  return <span className="rounded-full bg-paper-2 px-2.5 py-0.5 text-xs font-bold text-muted ring-1 ring-line">{label}</span>
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
        <div role="status" className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 animate-pop items-center gap-2 rounded-full bg-ink px-5 py-3 font-bold text-paper shadow-soft">
          <CheckCircle2 className="size-5 text-correct-light" aria-hidden />
          {msg}
        </div>
      )}
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)
