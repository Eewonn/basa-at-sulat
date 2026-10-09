import * as Popover from '@radix-ui/react-popover'
import { useQuery } from '@tanstack/react-query'
import { Cpu, WifiOff } from 'lucide-react'
import { api } from '@/api'
import { useT } from '@/strings'

function Dot({ ok }: { ok: boolean }) {
  return <span className={`inline-block size-2.5 rounded-full ${ok ? 'bg-correct-light' : 'bg-accent-light'}`} />
}

// Always visible: tells judges and teachers that everything runs on this laptop.
export function StatusPill() {
  const t = useT()
  const { data } = useQuery({ queryKey: ['health'], queryFn: () => api.health(), refetchInterval: 10_000 })
  const aligner = data?.models.aligner === 'loaded'
  const ollama = data?.models.ollama === 'up'

  return (
    <Popover.Root>
      <Popover.Trigger className="w-full cursor-pointer rounded-card bg-ink-2 p-3 text-left ring-1 ring-ink-3 transition hover:bg-ink-3">
        <div className="flex items-center gap-2 text-sm font-bold text-paper">
          <Cpu className="size-4 text-correct-light" aria-hidden />
          {t.statusLocal}
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs text-[#c9cfdf]">
          <WifiOff className="size-3.5" aria-hidden />
          {t.statusNoInternet}
          <span className="ml-auto flex gap-1" aria-hidden>
            <Dot ok={aligner} />
            <Dot ok={ollama} />
          </span>
        </div>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side="right"
          align="end"
          sideOffset={12}
          className="z-50 w-72 rounded-card bg-card p-4 text-sm text-body shadow-soft ring-1 ring-line"
        >
          <ul className="space-y-2">
            {[
              [t.statusAligner, aligner],
              [t.statusOllama, ollama]
            ].map(([name, ok]) => (
              <li key={String(name)} className="flex items-center gap-2">
                <Dot ok={Boolean(ok)} />
                <span className="flex-1">{name}</span>
                <span className="font-bold text-ink">{ok ? t.statusReady : t.statusDown}</span>
              </li>
            ))}
          </ul>
          {api.mode === 'mock' && (
            <p className="mt-3 rounded-lg bg-accent-bg px-3 py-2 text-xs font-bold text-[#8a3d12]">{t.statusMock}</p>
          )}
          <Popover.Arrow className="fill-card" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
