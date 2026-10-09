// Our original mascot: a friendly tamaraw (Mindoro dwarf buffalo). Pure SVG, no assets.
export type Mood = 'idle' | 'happy' | 'listening' | 'encourage' | 'thinking'

const FUR = '#5B4636'
const FUR_DARK = '#46362A'
const HORN = '#D9C7A6'
const MUZZLE = '#E3CDB2'
const NAVY = '#1E2A5A'

function Eyes({ mood }: { mood: Mood }) {
  if (mood === 'happy') {
    return (
      <g stroke={NAVY} strokeWidth="6" strokeLinecap="round" fill="none">
        <path d="M66 96 q12 -14 24 0" />
        <path d="M110 96 q12 -14 24 0" />
      </g>
    )
  }
  const look = mood === 'thinking' ? -5 : 0
  return (
    <g className="animate-blink" style={{ transformOrigin: '100px 96px', transformBox: 'view-box' }}>
      <circle cx="78" cy="96" r="13" fill="#fff" />
      <circle cx="122" cy="96" r="13" fill="#fff" />
      <circle cx="80" cy={98 + look} r="7.5" fill={NAVY} />
      <circle cx="124" cy={98 + look} r="7.5" fill={NAVY} />
      <circle cx="82.5" cy={95 + look} r="2.6" fill="#fff" />
      <circle cx="126.5" cy={95 + look} r="2.6" fill="#fff" />
    </g>
  )
}

function Mouth({ mood, talk }: { mood: Mood; talk?: number }) {
  // While the child speaks, Taw's mouth opens with their voice.
  if (talk !== undefined) return <ellipse cx="100" cy="150" rx={7 + talk * 5} ry={2 + talk * 11} fill="#C2404F" />
  if (mood === 'thinking') return <circle cx="100" cy="150" r="5" fill={FUR_DARK} />
  if (mood === 'happy') return <path d="M86 146 q14 16 28 0 z" fill="#C2404F" />
  return <path d="M90 148 q10 8 20 0" stroke={FUR_DARK} strokeWidth="4" strokeLinecap="round" fill="none" />
}

export function Tamaraw({
  mood = 'idle',
  size = 160,
  className = '',
  talk,
  dance = false
}: {
  mood?: Mood
  size?: number
  className?: string
  talk?: number
  dance?: boolean
}) {
  const wiggle = (talk ?? 0) * 22
  const leftEar = mood === 'listening' ? `rotate(${-28 - wiggle} 46 86)` : 'rotate(-8 46 86)'
  const rightEar = `rotate(${8 + wiggle} 154 86)`
  return (
    <svg
      viewBox="0 0 200 200"
      width={size}
      height={size}
      role="img"
      aria-label="Tamaraw"
      className={`${dance ? 'animate-dance' : mood === 'happy' ? 'animate-bounce-soft' : 'animate-float'} ${className}`}
    >
      {/* horns: short and V-shaped, like a real tamaraw */}
      <path d="M70 64 C64 54 62 44 64 34 C72 40 80 48 88 58 Z" fill={HORN} />
      <path d="M130 64 C136 54 138 44 136 34 C128 40 120 48 112 58 Z" fill={HORN} />
      {/* ears */}
      <ellipse cx="46" cy="86" rx="20" ry="11" fill={FUR} transform={leftEar} />
      <ellipse cx="154" cy="86" rx="20" ry="11" fill={FUR} transform={rightEar} />
      <ellipse cx="46" cy="86" rx="11" ry="5" fill="#E9A3A6" transform={leftEar} />
      <ellipse cx="154" cy="86" rx="11" ry="5" fill="#E9A3A6" transform={rightEar} />
      {/* head */}
      <ellipse cx="100" cy="108" rx="58" ry="56" fill={FUR} />
      <path d="M86 58 q14 12 28 0 q-2 14 -14 18 q-12 -4 -14 -18 z" fill={FUR_DARK} />
      {/* cheeks */}
      <ellipse cx="62" cy="122" rx="11" ry="7" fill="#F08A9B" opacity="0.55" />
      <ellipse cx="138" cy="122" rx="11" ry="7" fill="#F08A9B" opacity="0.55" />
      <Eyes mood={mood} />
      {/* muzzle */}
      <ellipse cx="100" cy="140" rx="34" ry="24" fill={MUZZLE} />
      <ellipse cx="88" cy="134" rx="4.5" ry="3.5" fill={FUR_DARK} />
      <ellipse cx="112" cy="134" rx="4.5" ry="3.5" fill={FUR_DARK} />
      <Mouth mood={mood} talk={talk} />
      {mood === 'thinking' && (
        <g fill="#2D5BD3">
          <circle cx="160" cy="44" r="6" />
          <circle cx="176" cy="30" r="8" />
          <circle cx="190" cy="12" r="10" />
        </g>
      )}
      {mood === 'happy' && (
        <g fill="#FFB627">
          <path d="M28 40 l4 10 l10 4 l-10 4 l-4 10 l-4 -10 l-10 -4 l10 -4 z" />
          <path d="M172 40 l3 8 l8 3 l-8 3 l-3 8 l-3 -8 l-8 -3 l8 -3 z" />
        </g>
      )}
    </svg>
  )
}
