// Illustrations by name. All art is our own (components/Art.tsx); "buffalo" is Taw himself.
import { Art } from './Art'
import { Tamaraw } from './Tamaraw'

export type EmojiName =
  | 'books'
  | 'chart'
  | 'fire'
  | 'glowingStar'
  | 'hibiscus'
  | 'hourglass'
  | 'house'
  | 'microphone'
  | 'school'
  | 'rice'
  | 'speaker'
  | 'star'
  | 'buffalo'

export function Emoji({ name, size = 48, className = '' }: { name: EmojiName; size?: number; className?: string }) {
  if (name === 'buffalo') return <Tamaraw size={size} className={className} />
  return <Art name={name} size={size} className={className} />
}
