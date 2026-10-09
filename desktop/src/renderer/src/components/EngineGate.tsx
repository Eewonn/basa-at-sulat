import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, enginePort } from '@/api'
import { Tamaraw } from './Tamaraw'
import { useT } from '@/strings'

// The app only shows what the engine computed, so nothing renders until it answers /health.
// The Electron main process starts the engine when the app opens (src/main/engine.ts).
export function EngineGate({ children }: { children: ReactNode }) {
  const { data, failureCount } = useQuery({
    queryKey: ['engineUp'],
    queryFn: () => api.health(),
    enabled: enginePort !== null,
    retry: true,
    retryDelay: 500,
    staleTime: Infinity
  })
  if (data?.ok) return children
  // Same limit as scripts/launch.py: the first start loads the aligner, slow laptops need longer.
  const gaveUp = failureCount * 0.5 > 180
  return <EngineScreen starting={enginePort !== null && !gaveUp} />
}

function EngineScreen({ starting }: { starting: boolean }) {
  const t = useT()
  return (
    <div className="paper flex h-full items-center justify-center bg-kid px-10">
      <div className="flex max-w-3xl items-center gap-10 rounded-card bg-white p-10 shadow-lift">
        <Tamaraw mood="thinking" size={200} />
        <div role="status">
          <h1 className="text-[34px] leading-tight font-black text-navy">{starting ? t.engineStartingTitle : t.engineMissingTitle}</h1>
          <p className="mt-3 text-lg font-semibold text-body">{starting ? t.engineStartingText : t.engineMissingText}</p>
          {!starting && <code className="mt-4 block rounded-tile bg-side px-4 py-3 text-base font-bold text-navy select-text">scripts/start.sh --check</code>}
        </div>
      </div>
    </div>
  )
}
