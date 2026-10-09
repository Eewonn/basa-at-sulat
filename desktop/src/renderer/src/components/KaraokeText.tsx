import type { BookWord } from '@/api/types'

// Read-along text: the word being spoken is highlighted; tapping a word jumps to it.
export function KaraokeText({ words, time, onSeek, size = 'text-[34px]' }: { words: BookWord[]; time: number; onSeek?: (t: number) => void; size?: string }) {
  const active = words.findIndex((w) => time >= w.start && time < w.end + 0.05)
  return (
    <p className={`flex flex-wrap gap-x-2 gap-y-2 leading-snug font-extrabold ${size}`}>
      {words.map((w, i) => (
        <button
          key={w.i}
          onClick={() => onSeek?.(w.start)}
          className={`cursor-pointer rounded-tile px-1.5 transition-colors ${
            i === active ? 'bg-sun-soft text-navy ring-3 ring-sun' : i < active ? 'text-navy' : 'text-body/70'
          }`}
        >
          {w.text}
        </button>
      ))}
    </p>
  )
}
