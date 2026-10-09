import { useId } from 'react'
import { TAW } from './TawLogo'

// Our original mascot: Taw, a friendly tamaraw (Mindoro dwarf buffalo). Same drawing as the logo
// (TawLogo.tsx) without the book, so the eyes, mouth and ears can react. Pure SVG, no assets.
export type Mood = 'idle' | 'happy' | 'listening' | 'encourage' | 'thinking'

const { ink: INK, fur: FUR, furShade: FUR_SHADE, tuft: TUFT, horn: HORN, muzzle: MUZZLE } = TAW
const HEAD = 'M120 50 C156 50 178 74 178 104 C178 124 172 140 164 150 C150 166 90 166 76 150 C68 140 62 124 62 104 C62 74 84 50 120 50 Z'
const ink = { stroke: INK, strokeWidth: 3.2, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const }

function Eyes({ mood }: { mood: Mood }) {
  if (mood === 'happy') {
    return (
      <g fill="none" {...ink} strokeWidth={5}>
        <path d="M82 108 q12 -15 24 0" />
        <path d="M134 108 q12 -15 24 0" />
      </g>
    )
  }
  const look = mood === 'thinking' ? -4 : 0
  return (
    <g className="animate-blink" style={{ transformOrigin: '120px 104px', transformBox: 'view-box' }}>
      <ellipse cx="94" cy="104" rx="13" ry="14" fill="#fff" {...ink} strokeWidth={2.6} />
      <ellipse cx="146" cy="104" rx="13" ry="14" fill="#fff" {...ink} strokeWidth={2.6} />
      <ellipse cx="96" cy={107 + look} rx="8.5" ry="9.5" fill="#24203A" />
      <ellipse cx="144" cy={107 + look} rx="8.5" ry="9.5" fill="#24203A" />
      <circle cx="99" cy={102.5 + look} r="3.2" fill="#fff" />
      <circle cx="147" cy={102.5 + look} r="3.2" fill="#fff" />
      <circle cx="93" cy={111 + look} r="1.6" fill="#fff" />
      <circle cx="141" cy={111 + look} r="1.6" fill="#fff" />
      <g {...ink} strokeWidth={2.6}>
        <path d="M81 99 l-6 -4" />
        <path d="M159 99 l6 -4" />
      </g>
    </g>
  )
}

function Mouth({ mood, talk }: { mood: Mood; talk?: number }) {
  // While the child speaks, Taw's mouth opens with their voice.
  if (talk !== undefined) return <ellipse cx="120" cy="153" rx={7 + talk * 5} ry={2 + talk * 10} fill="#C2404F" {...ink} strokeWidth={2.4} />
  if (mood === 'thinking') return <circle cx="120" cy="153" r="4.5" fill={INK} />
  if (mood === 'happy') return <path d="M106 148 q14 18 28 0 Z" fill="#C2404F" {...ink} strokeWidth={2.6} />
  return <path d="M109 150 q11 13 22 0 Z" fill="#C2404F" {...ink} strokeWidth={2.6} />
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
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const wiggle = (talk ?? 0) * 22
  const leftEar = mood === 'listening' ? `rotate(${28 + wiggle} 68 100)` : 'rotate(0 68 100)'
  const rightEar = `rotate(${-wiggle} 172 100)`

  return (
    <svg
      viewBox="10 -16 220 220"
      width={size}
      height={size}
      role="img"
      aria-label="Tamaraw"
      className={`${dance ? 'animate-dance' : mood === 'happy' ? 'animate-bounce-soft' : 'animate-float'} ${className}`}
    >
      <defs>
        {/* Nudges every line a little so nothing is perfectly geometric. */}
        <filter id={`${id}w`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" />
          <feDisplacementMap in="SourceGraphic" scale="3.5" xChannelSelector="R" yChannelSelector="G" />
        </filter>
        <clipPath id={`${id}h`}>
          <path d={HEAD} />
        </clipPath>
      </defs>

      <g>
        <g filter={`url(#${id}w)`}>
          {/* palay sprig tucked behind the ear */}
          <path d="M30 44 C40 58 50 74 60 96" fill="none" stroke="#B98A2E" strokeWidth="3" strokeLinecap="round" />
          <g fill="#E9B23C" stroke={INK} strokeWidth="1.8">
            <ellipse cx="33" cy="44" rx="4" ry="7" transform="rotate(-30 33 44)" />
            <ellipse cx="44" cy="52" rx="4" ry="7" transform="rotate(-62 44 52)" />
            <ellipse cx="34" cy="58" rx="4" ry="7" transform="rotate(-8 34 58)" />
            <ellipse cx="49" cy="64" rx="4" ry="7" transform="rotate(-66 49 64)" />
            <ellipse cx="40" cy="70" rx="4" ry="7" transform="rotate(-14 40 70)" />
          </g>

          {/* horns: short and V-shaped, with growth ridges */}
          <path d="M86 62 C80 50 74 40 70 28 C82 32 94 42 100 56 Z" fill={HORN} {...ink} />
          <path d="M154 62 C160 50 166 40 170 28 C158 32 146 42 140 56 Z" fill={HORN} {...ink} />
          <g fill="none" stroke="#B9A47E" strokeWidth="2" strokeLinecap="round">
            <path d="M75 39 q6 1 10 6" />
            <path d="M80 48 q6 1 9 6" />
            <path d="M165 39 q-6 1 -10 6" />
            <path d="M160 48 q-6 1 -9 6" />
          </g>

          {/* ears: they perk up to listen and wiggle with the child's voice */}
          <g transform={leftEar}>
            <path d="M68 96 C52 82 32 84 20 94 C32 106 52 108 70 104 Z" fill={FUR} {...ink} />
            <path d="M60 97 C50 91 38 92 30 96 C40 102 52 103 61 101 Z" fill="#EFA7A9" />
          </g>
          <g transform={rightEar}>
            <path d="M172 96 C188 82 208 84 220 94 C208 106 188 108 170 104 Z" fill={FUR} {...ink} />
            <path d="M180 97 C190 91 202 92 210 96 C200 102 188 103 179 101 Z" fill="#EFA7A9" />
          </g>

          {/* head with shading on one side */}
          <path d={HEAD} fill={FUR} />
          <ellipse cx="184" cy="108" rx="34" ry="64" fill={FUR_SHADE} clipPath={`url(#${id}h)`} />
          <path d={HEAD} fill="none" {...ink} />

          {/* forehead tuft */}
          <path d="M102 60 L108 47 L114 57 L120 43 L126 57 L132 47 L138 60 Q120 70 102 60 Z" fill={TUFT} {...ink} strokeWidth={2.4} />

          {/* brows: raised when thinking */}
          <g fill="none" {...ink}>
            <path d={mood === 'thinking' ? 'M82 82 q10 -9 20 -4' : 'M82 86 q10 -7 20 -2'} />
            <path d={mood === 'thinking' ? 'M138 80 q10 -7 20 2' : 'M138 84 q10 -5 20 2'} />
          </g>
          <Eyes mood={mood} />

          {/* blush, hatched like crayon */}
          <ellipse cx="76" cy="128" rx="12" ry="7" fill="#F2869A" opacity="0.5" />
          <ellipse cx="164" cy="128" rx="12" ry="7" fill="#F2869A" opacity="0.5" />
          <g stroke="#D4566F" strokeWidth="2" strokeLinecap="round">
            <path d="M70 131 l4 -6" />
            <path d="M76 132 l4 -6" />
            <path d="M82 131 l4 -6" />
            <path d="M158 131 l4 -6" />
            <path d="M164 132 l4 -6" />
            <path d="M170 131 l4 -6" />
          </g>

          {/* muzzle */}
          <path d="M120 116 C146 116 160 128 160 144 C160 160 142 168 120 168 C98 168 80 160 80 144 C80 128 94 116 120 116 Z" fill={MUZZLE} {...ink} />
          <path d="M106 133 q-7 2 -5 9 q5 -1 7 -6 Z" fill={INK} />
          <path d="M134 133 q7 2 5 9 q-5 -1 -7 -6 Z" fill={INK} />
          <Mouth mood={mood} talk={talk} />
        </g>

        {mood === 'thinking' && (
          <g fill="#fff" {...ink} strokeWidth={2.4}>
            <circle cx="186" cy="50" r="6" />
            <circle cx="202" cy="36" r="8" />
            <circle cx="216" cy="18" r="9" />
          </g>
        )}
        {mood === 'happy' && (
          <g fill="#FFB627" {...ink} strokeWidth={2}>
            <path d="M200 30 l4 10 l10 4 l-10 4 l-4 10 l-4 -10 l-10 -4 l10 -4 z" />
            <path d="M68 6 l3 8 l8 3 l-8 3 l-3 8 l-3 -8 l-8 -3 l8 -3 z" />
          </g>
        )}
      </g>
    </svg>
  )
}
