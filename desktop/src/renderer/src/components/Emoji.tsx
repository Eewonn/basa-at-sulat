// Microsoft Fluent Emoji (Flat), MIT License: bundled so they work offline.
import books from '@/assets/emoji/books.svg'
import chart from '@/assets/emoji/chart_increasing.svg'
import fire from '@/assets/emoji/fire.svg'
import glowingStar from '@/assets/emoji/glowing_star.svg'
import hibiscus from '@/assets/emoji/hibiscus.svg'
import hourglass from '@/assets/emoji/hourglass_not_done.svg'
import house from '@/assets/emoji/house_with_garden.svg'
import microphone from '@/assets/emoji/microphone.svg'
import school from '@/assets/emoji/school.svg'
import rice from '@/assets/emoji/sheaf_of_rice.svg'
import speaker from '@/assets/emoji/speaker_high_volume.svg'
import star from '@/assets/emoji/star.svg'
import buffalo from '@/assets/emoji/water_buffalo.svg'

const EMOJI = { books, chart, fire, glowingStar, hibiscus, hourglass, house, microphone, school, rice, speaker, star, buffalo }
export type EmojiName = keyof typeof EMOJI

export function Emoji({ name, size = 48, className = '' }: { name: EmojiName; size?: number; className?: string }) {
  return <img src={EMOJI[name]} width={size} height={size} alt="" draggable={false} className={className} />
}
