import * as Popover from '@radix-ui/react-popover'
import { useState } from 'react'
import { Check, CircleDashed, TriangleAlert, Volume2 } from 'lucide-react'
import type { Word, WordLabel } from '@/api/types'
import { useT } from '@/strings'

const STYLE: Record<WordLabel, string> = {
  matched: 'text-navy hover:bg-blue-soft',
  misread: 'bg-coral-soft text-navy ring-3 ring-coral',
  skipped: 'text-[#4b5263] outline-3 outline-dashed outline-muted -outline-offset-3'
}

// One word of the passage. Flagged words always show their label as text, not just color.
// clipUrl is the child's own reading of this word, so the teacher can hear a flag before fixing it.
export function WordChip({
  word,
  delayMs,
  onFix,
  pauseBefore,
  clipUrl
}: {
  word: Word
  delayMs: number
  onFix: (label: WordLabel) => void
  pauseBefore?: number
  clipUrl?: string
}) {
  const t = useT()
  const labelText = { matched: t.labelMatched, misread: t.labelMisread, skipped: t.labelSkipped }
  const [playing, setPlaying] = useState(false)
  const hear = () => {
    if (!clipUrl) return
    const audio = new Audio(clipUrl)
    const done = () => setPlaying(false)
    audio.onended = done
    audio.onerror = done
    setPlaying(true)
    audio.play().catch(done)
  }

  return (
    <Popover.Root>
      <Popover.Trigger
        className={`group flex cursor-pointer animate-word-in flex-col items-center rounded-tile px-2.5 py-1 transition ${STYLE[word.label]}`}
        style={{ animationDelay: `${delayMs}ms` }}
        aria-label={`${word.text}: ${labelText[word.label]}`}
      >
        <span className="text-[34px] leading-tight font-extrabold">{word.text}</span>
        {word.label !== 'matched' && (
          <span
            className={`flex items-center gap-1 text-xs font-extrabold ${word.label === 'misread' ? 'text-coral-ink' : 'text-[#4b5263]'}`}
          >
            {word.label === 'misread' ? <TriangleAlert className="size-3.5" aria-hidden /> : <CircleDashed className="size-3.5" aria-hidden />}
            {labelText[word.label]}
          </span>
        )}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content sideOffset={8} className="z-50 w-64 rounded-tile bg-white p-3 shadow-lift">
          <div className="flex items-center justify-between gap-2">
            <p className="text-2xl font-black text-navy">{word.text}</p>
            {clipUrl && (
              <button
                onClick={hear}
                disabled={playing}
                className="flex cursor-pointer items-center gap-1.5 rounded-full bg-blue px-3 py-1.5 text-sm font-extrabold text-white transition hover:bg-blue-dark disabled:opacity-60"
              >
                <Volume2 className={`size-4 ${playing ? 'animate-pulse' : ''}`} aria-hidden /> {t.hearWord}
              </button>
            )}
          </div>
          {(word.label !== 'matched' || pauseBefore) && (
            <div className="mt-3 rounded-lg bg-sun-soft px-3 py-2 text-sm text-navy">
              <p className="font-extrabold">{t.whyTitle}</p>
              <ul className="mt-1 space-y-0.5 font-semibold">
                {word.label === 'misread' && <li>{t.whyMisread(Math.round(word.score * 100))}</li>}
                {word.label === 'skipped' && <li>{t.whySkipped}</li>}
                {pauseBefore ? <li>{t.whyPause(pauseBefore.toFixed(1))}</li> : null}
              </ul>
              <p className="mt-1 text-xs font-bold text-body">{t.whyCheck}</p>
            </div>
          )}
          <p className="mt-3 mb-1.5 text-xs font-extrabold tracking-wider text-muted uppercase">{t.fixAs}</p>
          <div className="grid gap-1.5">
            {(['matched', 'misread', 'skipped'] as const).map((l) => (
              <Popover.Close
                key={l}
                onClick={() => onFix(l)}
                className={`flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-left font-bold transition ${
                  word.label === l ? 'bg-blue text-white' : 'bg-side text-navy hover:bg-blue-soft'
                }`}
              >
                {l === 'matched' ? <Check className="size-4" /> : l === 'misread' ? <TriangleAlert className="size-4" /> : <CircleDashed className="size-4" />}
                {labelText[l]}
              </Popover.Close>
            ))}
          </div>
          <Popover.Arrow className="fill-white" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
