// Our own illustration set, drawn to match Taw: flat shapes, soft highlights, no outlines.
// Pieces that sit on colored buttons/cards (mic, speaker, clock) use light colors on purpose.
import type { ReactElement } from 'react'

const SUN = '#FFB627'
const SUN_LIGHT = '#FFD36B'
const CORAL = '#D62F55'
const BLUE = '#2D5BD3'
const TEAL = '#17885A'
const CREAM = '#FFF6E2'
const BANIG = '#E9D3A6'
const NIPA = '#C9A15A'
const BROWN = '#5B4636'
const BROWN_DARK = '#46362A'
const NAVY = '#1E2A5A'

const STAR = '32.0,9.0 38.8,24.7 55.8,26.3 42.9,37.6 46.7,54.2 32.0,45.5 17.3,54.2 21.1,37.6 8.2,26.3 25.2,24.7'
const STAR_HI = '29.0,21.0 31.7,27.3 38.5,27.9 33.4,32.4 34.9,39.1 29.0,35.6 23.1,39.1 24.6,32.4 19.5,27.9 26.3,27.3'

const star = (
  <>
    <polygon points={STAR} fill={SUN} stroke={SUN} strokeWidth="6" strokeLinejoin="round" />
    <polygon points={STAR_HI} fill={SUN_LIGHT} stroke={SUN_LIGHT} strokeWidth="3" strokeLinejoin="round" />
    <ellipse cx="24" cy="24" rx="3" ry="2" fill="#fff" opacity="0.7" transform="rotate(-35 24 24)" />
  </>
)

export const ART: Record<string, ReactElement> = {
  star,

  glowingStar: (
    <>
      <g stroke={SUN} strokeWidth="3.5" strokeLinecap="round">
        <path d="M32 2v5M32 58v4M4 34h5M55 34h5M11 12l4 4M53 12l-4 4" />
      </g>
      <g transform="translate(6.4 6.8) scale(0.8)">{star}</g>
    </>
  ),

  fire: (
    <>
      <path d="M32 4C38 16 52 24 51 41c-1 13-9 19-19 19S13 54 13 41c0-11 7-16 9-25 4 6 6 9 9 10 2-7 3-14 1-22Z" fill={CORAL} />
      <path d="M32 26c3 7 11 12 10 21-1 7-5 10-10 10s-10-3-10-10c0-5 3-8 5-12 2 3 3 4 4 4 1-4 1-8 1-13Z" fill={SUN} />
      <path d="M32 42c2 3 4 5 4 8 0 3-2 5-4 5s-4-2-4-5c0-3 2-5 4-8Z" fill={CREAM} />
    </>
  ),

  // Orasan: a classic two-bell alarm clock.
  hourglass: (
    <>
      <circle cx="16" cy="14" r="8" fill={SUN} />
      <circle cx="48" cy="14" r="8" fill={SUN} />
      <path d="M18 56l-5 6M46 56l5 6" stroke={BROWN_DARK} strokeWidth="4" strokeLinecap="round" />
      <circle cx="32" cy="36" r="24" fill={SUN} />
      <circle cx="32" cy="36" r="18" fill={CREAM} />
      <path d="M32 36V24M32 36l8 5" stroke={NAVY} strokeWidth="4" strokeLinecap="round" />
      <circle cx="32" cy="36" r="3" fill={CORAL} />
    </>
  ),

  microphone: (
    <>
      <path d="M18 30c0 8 6 15 14 15s14-7 14-15" fill="none" stroke={CREAM} strokeWidth="4" strokeLinecap="round" />
      <path d="M32 45v10M23 58h18" stroke={CREAM} strokeWidth="4" strokeLinecap="round" />
      <rect x="22" y="4" width="20" height="34" rx="10" fill={CREAM} />
      <path d="M22 16h20M22 24h20" stroke={NAVY} strokeWidth="2.5" opacity="0.35" />
      <ellipse cx="27" cy="11" rx="2" ry="3.5" fill="#fff" />
    </>
  ),

  speaker: (
    <>
      <path d="M8 24h10l14-12v40L18 40H8Z" fill={CREAM} />
      <path d="M41 23c4 3 6 6 6 9s-2 6-6 9M47 15c7 5 11 11 11 17s-4 12-11 17" fill="none" stroke={SUN} strokeWidth="4.5" strokeLinecap="round" />
    </>
  ),

  books: (
    <>
      <rect x="8" y="44" width="48" height="12" rx="3" fill={BLUE} />
      <rect x="11" y="47" width="42" height="3" rx="1.5" fill={CREAM} />
      <rect x="12" y="31" width="42" height="12" rx="3" fill={TEAL} />
      <rect x="15" y="34" width="36" height="3" rx="1.5" fill={CREAM} />
      <rect x="10" y="18" width="40" height="12" rx="3" fill={SUN} transform="rotate(-6 30 24)" />
      <rect x="40" y="10" width="5" height="14" rx="1" fill={CORAL} transform="rotate(-6 30 24)" />
    </>
  ),

  chart: (
    <>
      <rect x="6" y="6" width="52" height="52" rx="10" fill={CREAM} />
      <path d="M16 46h34M16 16v30" stroke={BANIG} strokeWidth="3" strokeLinecap="round" />
      <path d="M18 40l10-9 7 5 13-15" fill="none" stroke={BLUE} strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="48" cy="21" r="5" fill={CORAL} />
    </>
  ),

  // Palay: two rice stalks heavy with golden grain.
  rice: (
    <>
      <path d="M26 60C26 44 22 28 14 16M38 60c0-16 4-30 12-42" fill="none" stroke={TEAL} strokeWidth="4" strokeLinecap="round" />
      <path d="M30 60c-2-8-8-12-14-12 6 1 10 4 12 8" fill={TEAL} />
      {[
        [14, 16], [17, 22], [12, 23], [20, 28], [15, 30], [22, 34],
        [50, 18], [47, 24], [52, 25], [44, 30], [49, 32], [42, 36]
      ].map(([x, y], i) => (
        <ellipse key={i} cx={x} cy={y} rx="3.4" ry="5" fill={i % 3 === 0 ? SUN_LIGHT : SUN} transform={`rotate(${x < 32 ? -30 : 30} ${x} ${y})`} />
      ))}
    </>
  ),

  // Bahay kubo: nipa roof, woven walls, bamboo stilts.
  house: (
    <>
      <path d="M18 46v14M46 46v14M32 46v14" stroke={BROWN} strokeWidth="4" strokeLinecap="round" />
      <rect x="12" y="28" width="40" height="20" rx="2" fill={BANIG} />
      <path d="M12 34h40M12 40h40M20 28v20M28 28v20M36 28v20M44 28v20" stroke="#D6BC88" strokeWidth="1.5" />
      <rect x="27" y="33" width="10" height="15" rx="1" fill={BROWN_DARK} />
      <path d="M4 32L32 6l28 26Z" fill={NIPA} />
      <path d="M12 26l20-14 20 14M18 30l14-10 14 10" stroke="#B08848" strokeWidth="2" fill="none" />
      <path d="M8 56h48" stroke={TEAL} strokeWidth="4" strokeLinecap="round" />
    </>
  ),

  // Gumamela (hibiscus).
  hibiscus: (
    <>
      <path d="M44 50c6 4 12 4 16 0-5-3-10-4-16 0Z" fill={TEAL} />
      {[0, 72, 144, 216, 288].map((a) => (
        <ellipse key={a} cx="32" cy="18" rx="11" ry="14" fill={CORAL} transform={`rotate(${a} 32 32)`} />
      ))}
      {[0, 72, 144, 216, 288].map((a) => (
        <ellipse key={`h${a}`} cx="32" cy="22" rx="4" ry="6" fill="#E85A79" transform={`rotate(${a} 32 32)`} />
      ))}
      <circle cx="32" cy="32" r="6" fill="#A8203F" />
      <path d="M32 32l12-14" stroke={SUN} strokeWidth="3" strokeLinecap="round" />
      <circle cx="45" cy="17" r="3" fill={SUN} />
    </>
  ),

  // Paaralan: a small school with the Philippine flag.
  school: (
    <>
      <path d="M50 6v22" stroke={BROWN_DARK} strokeWidth="2.5" strokeLinecap="round" />
      <path d="M50 7h11v4H50Z" fill={BLUE} />
      <path d="M50 11h11v4H50Z" fill={CORAL} />
      <path d="M50 7l5 4-5 4Z" fill="#fff" />
      <circle cx="51.8" cy="11" r="0.9" fill={SUN} />
      <rect x="6" y="30" width="52" height="28" rx="2" fill={CREAM} />
      <path d="M2 32L32 16l30 16Z" fill={CORAL} />
      <rect x="27" y="40" width="10" height="18" rx="1" fill={BLUE} />
      <rect x="11" y="37" width="10" height="9" rx="1" fill={TEAL} />
      <rect x="43" y="37" width="10" height="9" rx="1" fill={TEAL} />
      <circle cx="32" cy="27" r="3.5" fill={SUN} />
    </>
  ),

  // The doodle used in place of the generic "sparkles" icon: a practice flashcard with a star.
  flashcard: (
    <>
      <rect x="10" y="14" width="42" height="32" rx="5" fill="none" stroke="currentColor" strokeWidth="5" transform="rotate(-8 31 30)" />
      <path d="M20 32h14M20 40h9" stroke="currentColor" strokeWidth="5" strokeLinecap="round" transform="rotate(-8 31 30)" />
      <polygon points="50,42 53,49 60,50 55,55 56,62 50,58 44,62 45,55 40,50 47,49" fill="currentColor" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </>
  )
}

export function Art({ name, size = 48, className = '' }: { name: string; size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} className={className} aria-hidden>
      {ART[name]}
    </svg>
  )
}
