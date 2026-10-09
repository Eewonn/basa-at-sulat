import * as Popover from '@radix-ui/react-popover'
import { Check, CircleDashed, TriangleAlert } from 'lucide-react'
import type { Word, WordLabel } from '@/api/types'
import { useT } from '@/strings'

const STYLE: Record<WordLabel, string> = {
  matched: 'text-ink hover:bg-paper-2',
  misread: 'bg-accent-bg text-ink ring-2 ring-accent',
  skipped: 'text-[#4b5263] outline-2 outline-dashed outline-muted -outline-offset-2'
}

// One word of the passage. Flagged words always show their label as text, not just color.
export function WordChip({ word, delayMs, onFix }: { word: Word; delayMs: number; onFix: (label: WordLabel) => void }) {
  const t = useT()
  const labelText = { matched: t.labelMatched, misread: t.labelMisread, skipped: t.labelSkipped }

  return (
    <Popover.Root>
      <Popover.Trigger
        className={`group flex cursor-pointer animate-word-in flex-col items-center rounded-xl px-2.5 py-1 transition ${STYLE[word.label]}`}
        style={{ animationDelay: `${delayMs}ms` }}
        aria-label={`${word.text}: ${labelText[word.label]}`}
      >
        <span className="font-display text-[34px] leading-tight font-bold">{word.text}</span>
        {word.label !== 'matched' && (
          <span
            className={`flex items-center gap-1 text-xs font-extrabold ${word.label === 'misread' ? 'text-[#8a3d12]' : 'text-[#4b5263]'}`}
          >
            {word.label === 'misread' ? <TriangleAlert className="size-3.5" aria-hidden /> : <CircleDashed className="size-3.5" aria-hidden />}
            {labelText[word.label]}
            {word.heard && ` · “${word.heard}”`}
          </span>
        )}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content sideOffset={8} className="z-50 w-64 rounded-card bg-card p-3 shadow-soft ring-1 ring-line">
          <p className="font-display text-2xl font-bold text-ink">{word.text}</p>
          {word.heard && (
            <p className="mt-1 text-sm text-body">
              {t.heard}: <b className="text-[#8a3d12]">“{word.heard}”</b>
            </p>
          )}
          <p className="mt-3 mb-1.5 text-xs font-extrabold tracking-wider text-muted uppercase">{t.fixAs}</p>
          <div className="grid gap-1.5">
            {(['matched', 'misread', 'skipped'] as const).map((l) => (
              <Popover.Close
                key={l}
                onClick={() => onFix(l)}
                className={`flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-left font-bold transition ${
                  word.label === l ? 'bg-ink text-paper' : 'bg-paper-2 text-ink hover:bg-line'
                }`}
              >
                {l === 'matched' ? <Check className="size-4" /> : l === 'misread' ? <TriangleAlert className="size-4" /> : <CircleDashed className="size-4" />}
                {labelText[l]}
              </Popover.Close>
            ))}
          </div>
          <Popover.Arrow className="fill-card" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
