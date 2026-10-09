import { Tamaraw } from './Tamaraw'
import { useT } from '@/strings'

// The app only shows what the engine computed, so without one there is nothing to show.
export function EngineMissing() {
  const t = useT()
  return (
    <div className="paper flex h-full items-center justify-center bg-kid px-10">
      <div className="flex max-w-3xl items-center gap-10 rounded-card bg-white p-10 shadow-lift">
        <Tamaraw mood="thinking" size={200} />
        <div>
          <h1 className="text-[34px] leading-tight font-black text-navy">{t.engineMissingTitle}</h1>
          <p className="mt-3 text-lg font-semibold text-body">{t.engineMissingText}</p>
          <code className="mt-4 block rounded-tile bg-side px-4 py-3 text-base font-bold text-navy select-text">scripts/start.sh</code>
        </div>
      </div>
    </div>
  )
}
