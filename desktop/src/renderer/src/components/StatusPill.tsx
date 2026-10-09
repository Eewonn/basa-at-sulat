import * as Popover from '@radix-ui/react-popover'
import { useQuery } from '@tanstack/react-query'
import { Cpu, WifiOff } from 'lucide-react'
import { api } from '@/api'
import { useT } from '@/strings'

function Dot({ ok }: { ok: boolean }) {
  return <span className={`inline-block size-2.5 rounded-full ${ok ? 'bg-teal' : 'bg-coral'}`} />
}

// Always visible: tells judges and teachers that everything runs on this laptop.
export function StatusPill() {
  const t = useT()
  const { data } = useQuery({ queryKey: ['health'], queryFn: () => api.health(), refetchInterval: 10_000 })
  const aligner = data?.models.aligner === 'loaded'
  const ollama = data?.models.ollama === 'up'

  return (
    <Popover.Root>
      <Popover.Trigger className="w-full cursor-pointer rounded-tile bg-white p-3 text-left shadow-soft transition hover:-translate-y-0.5">
        <div className="flex items-center gap-2 text-sm font-extrabold text-navy">
          <Cpu className="size-4 text-teal-ink" aria-hidden />
          {t.statusLocal}
          <span className="ml-auto flex gap-1" aria-hidden>
            <Dot ok={aligner} />
            <Dot ok={ollama} />
          </span>
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs font-semibold text-body">
          <WifiOff className="size-3.5" aria-hidden />
          {t.statusNoInternet}
        </div>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content side="right" align="end" sideOffset={12} className="z-50 w-72 rounded-tile bg-white p-4 text-sm text-body shadow-lift">
          <ul className="space-y-2">
            {[
              [t.statusAligner, aligner],
              [t.statusOllama, ollama]
            ].map(([name, ok]) => (
              <li key={String(name)} className="flex items-center gap-2">
                <Dot ok={Boolean(ok)} />
                <span className="flex-1">{name}</span>
                <span className="font-extrabold text-navy">{ok ? t.statusReady : t.statusDown}</span>
              </li>
            ))}
          </ul>
          {api.mode === 'mock' && <p className="mt-3 rounded-lg bg-sun-soft px-3 py-2 text-xs font-bold text-[#6b4f00]">{t.statusMock}</p>}
          <Popover.Arrow className="fill-white" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
