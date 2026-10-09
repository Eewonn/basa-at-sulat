import { useId } from 'react'

const INK = '#6B3FA0' // the violet stamp-pad ink every Filipino classroom knows

// The teacher's "VG / Very Good!" rubber stamp, with a slightly uneven ink texture.
export function Stamp({ size = 180, className = '', animate = true }: { size?: number; className?: string; animate?: boolean }) {
  const id = useId().replace(/:/g, '')
  return (
    <svg
      viewBox="0 0 200 200"
      width={size}
      height={size}
      role="img"
      aria-label="VG, Very Good!"
      className={`${animate ? 'animate-stamp' : ''} ${className}`}
      style={{ rotate: '-12deg' }}
    >
      <defs>
        <filter id={`ink-${id}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="2" seed="7" />
          <feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 -3 2.75" />
          <feComposite in="SourceGraphic" operator="in" />
        </filter>
        <path id={`arc-${id}`} d="M38 112 A62 62 0 0 0 162 112" />
      </defs>
      <g filter={`url(#ink-${id})`} fill={INK} stroke={INK}>
        <circle cx="100" cy="100" r="90" fill="none" strokeWidth="9" />
        <circle cx="100" cy="100" r="76" fill="none" strokeWidth="3" />
        <polygon
          points="100,38 106,52 121,53 110,63 113,78 100,70 87,78 90,63 79,53 94,52"
          strokeWidth="3"
          strokeLinejoin="round"
        />
        <text x="100" y="118" textAnchor="middle" fontSize="54" fontWeight="900" stroke="none" style={{ fontFamily: 'var(--font-hand), var(--font-sans)' }}>
          VG
        </text>
        <text fontSize="22" fontWeight="900" stroke="none" letterSpacing="2" style={{ fontFamily: 'var(--font-hand), var(--font-sans)' }}>
          <textPath href={`#arc-${id}`} startOffset="50%" textAnchor="middle">
            VERY GOOD!
          </textPath>
        </text>
      </g>
    </svg>
  )
}
