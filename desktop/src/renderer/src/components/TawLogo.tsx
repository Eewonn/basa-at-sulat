import { useId } from 'react'

// The app's logo: Taw peeking over an open book, drawn like a children's-book illustration
// (brown ink outlines, a slight hand-cut wobble, hatched blush) and cut out like a sticker.
// The animated mascot used inside the app stays in Tamaraw.tsx.
const INK = '#3B2A1F'
const FUR = '#6B5140'
const FUR_SHADE = '#553F31'
const TUFT = '#46352A'
const HORN = '#EADBB9'
const MUZZLE = '#EBD6BC'
const PAGE = '#FBF3DF'

export function TawLogo({ size = 240, className = '' }: { size?: number; className?: string }) {
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const ink = { stroke: INK, strokeWidth: 3.2, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const }

  return (
    <svg viewBox="0 0 240 240" width={size} height={size} role="img" aria-label="Taw" className={className}>
      <defs>
        {/* White die-cut border plus a soft shadow, like a sticker on a notebook. */}
        <filter id={`${id}s`} x="-20%" y="-20%" width="140%" height="140%">
          <feMorphology in="SourceAlpha" operator="dilate" radius="7" result="grow" />
          <feFlood floodColor="#fff" />
          <feComposite in2="grow" operator="in" result="outline" />
          <feOffset in="grow" dy="5" result="off" />
          <feGaussianBlur in="off" stdDeviation="5" result="blur" />
          <feFlood floodColor="#1E2A5A" floodOpacity="0.18" />
          <feComposite in2="blur" operator="in" result="shadow" />
          <feMerge>
            <feMergeNode in="shadow" />
            <feMergeNode in="outline" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        {/* Nudges every line a little so nothing is perfectly geometric. */}
        <filter id={`${id}w`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" />
          <feDisplacementMap in="SourceGraphic" scale="3.5" xChannelSelector="R" yChannelSelector="G" />
        </filter>
        <clipPath id={`${id}h`}>
          <path d="M120 50 C156 50 178 74 178 104 C178 124 172 140 164 150 L76 150 C68 140 62 124 62 104 C62 74 84 50 120 50 Z" />
        </clipPath>
      </defs>

      <g filter={`url(#${id}s)`}>
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

          {/* ears */}
          <path d="M68 96 C52 82 32 84 20 94 C32 106 52 108 70 104 Z" fill={FUR} {...ink} />
          <path d="M60 97 C50 91 38 92 30 96 C40 102 52 103 61 101 Z" fill="#EFA7A9" />
          <path d="M172 96 C188 82 208 84 220 94 C208 106 188 108 170 104 Z" fill={FUR} {...ink} />
          <path d="M180 97 C190 91 202 92 210 96 C200 102 188 103 179 101 Z" fill="#EFA7A9" />

          {/* shoulders, hidden mostly behind the book */}
          <path d="M70 146 C60 158 54 170 54 182 L186 182 C186 170 180 158 170 146 Z" fill={FUR} {...ink} />

          {/* head with shading on one side */}
          <path d="M120 50 C156 50 178 74 178 104 C178 124 172 140 164 150 L76 150 C68 140 62 124 62 104 C62 74 84 50 120 50 Z" fill={FUR} />
          <ellipse cx="184" cy="108" rx="34" ry="64" fill={FUR_SHADE} clipPath={`url(#${id}h)`} />
          <path d="M164 150 C172 140 178 124 178 104 C178 74 156 50 120 50 C84 50 62 74 62 104 C62 124 68 140 76 150" fill="none" {...ink} />

          {/* forehead tuft */}
          <path d="M102 60 L108 47 L114 57 L120 43 L126 57 L132 47 L138 60 Q120 70 102 60 Z" fill={TUFT} {...ink} strokeWidth={2.4} />

          {/* brows and eyes */}
          <g fill="none" {...ink}>
            <path d="M82 86 q10 -7 20 -2" />
            <path d="M138 84 q10 -5 20 2" />
          </g>
          <ellipse cx="94" cy="104" rx="13" ry="14" fill="#fff" {...ink} strokeWidth={2.6} />
          <ellipse cx="146" cy="104" rx="13" ry="14" fill="#fff" {...ink} strokeWidth={2.6} />
          <ellipse cx="96" cy="107" rx="8.5" ry="9.5" fill="#24203A" />
          <ellipse cx="144" cy="107" rx="8.5" ry="9.5" fill="#24203A" />
          <circle cx="99" cy="102.5" r="3.2" fill="#fff" />
          <circle cx="147" cy="102.5" r="3.2" fill="#fff" />
          <circle cx="93" cy="111" r="1.6" fill="#fff" />
          <circle cx="141" cy="111" r="1.6" fill="#fff" />
          <g {...ink} strokeWidth={2.6}>
            <path d="M81 99 l-6 -4" />
            <path d="M159 99 l6 -4" />
          </g>

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
          <path d="M109 150 q11 13 22 0 Z" fill="#C2404F" {...ink} strokeWidth={2.6} />

          {/* the open book, with pad-paper lines */}
          <path d="M38 180 Q120 168 202 180 L206 216 Q120 206 34 216 Z" fill="#D62F55" {...ink} />
          <path d="M46 176 Q84 164 120 180 L120 208 Q84 196 42 206 Z" fill={PAGE} {...ink} />
          <path d="M194 176 Q156 164 120 180 L120 208 Q156 196 198 206 Z" fill={PAGE} {...ink} />
          <g fill="none" stroke="#9DB4E8" strokeWidth="2" strokeLinecap="round">
            <path d="M54 186 Q86 178 112 189" />
            <path d="M52 195 Q86 187 112 198" />
            <path d="M186 186 Q154 178 128 189" />
            <path d="M188 195 Q154 187 128 198" />
          </g>

          {/* hooves resting on the pages */}
          <path d="M66 156 C60 166 62 176 68 182 L92 182 C94 172 92 164 88 156 Z" fill={FUR} {...ink} />
          <path d="M66 180 C66 190 94 190 94 180 Z" fill="#4A3426" {...ink} strokeWidth={2.6} />
          <path d="M80 182 l0 6" stroke="#A88D74" strokeWidth="2" strokeLinecap="round" />
          <path d="M174 156 C180 166 178 176 172 182 L148 182 C146 172 148 164 152 156 Z" fill={FUR} {...ink} />
          <path d="M174 180 C174 190 146 190 146 180 Z" fill="#4A3426" {...ink} strokeWidth={2.6} />
          <path d="M160 182 l0 6" stroke="#A88D74" strokeWidth="2" strokeLinecap="round" />
        </g>
      </g>
    </svg>
  )
}
