// Kid-mode sound effects, synthesized with Web Audio: no audio files, works offline.
// Never call these while the mic is recording, or they end up in the child's audio.

let ctx: AudioContext | null = null

export function isMuted(): boolean {
  try {
    return localStorage.getItem('sfxMuted') === '1'
  } catch {
    return false
  }
}

export function setMuted(muted: boolean): void {
  try {
    localStorage.setItem('sfxMuted', muted ? '1' : '0')
  } catch {
    // Mute just won't persist.
  }
}

function tone(freq: number, start: number, length: number, type: OscillatorType = 'sine', volume = 0.18, slideTo?: number) {
  if (!ctx) return
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  const t0 = ctx.currentTime + start
  osc.type = type
  osc.frequency.setValueAtTime(freq, t0)
  if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, t0 + length)
  gain.gain.setValueAtTime(0.0001, t0)
  gain.gain.exponentialRampToValueAtTime(volume, t0 + 0.015)
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + length)
  osc.connect(gain).connect(ctx.destination)
  osc.start(t0)
  osc.stop(t0 + length + 0.05)
}

function play(fn: () => void) {
  if (isMuted()) return
  ctx ??= new AudioContext()
  void ctx.resume()
  fn()
}

// C major notes, a friendly key for kids.
const C5 = 523.25, E5 = 659.25, G5 = 783.99, C6 = 1046.5, E6 = 1318.5, G6 = 1568

export const sfx = {
  pop: () => play(() => tone(620, 0, 0.09, 'sine', 0.14, 900)),
  chime: () =>
    play(() => {
      tone(C6, 0, 0.35, 'triangle')
      tone(E6, 0.09, 0.45, 'triangle')
    }),
  sparkle: () =>
    play(() => {
      ;[G6, E6 * 1.5, C6 * 2].forEach((f, i) => tone(f, i * 0.05, 0.18, 'sine', 0.08))
    }),
  // Gentle and playful: a soft bounce, never a buzzer.
  boing: () => play(() => tone(330, 0, 0.32, 'sine', 0.16, 220)),
  combo: () =>
    play(() => {
      ;[C5, E5, G5, C6, E6].forEach((f, i) => tone(f, i * 0.06, 0.2, 'triangle', 0.12))
    }),
  // A soft rubber-stamp "thud".
  stamp: () =>
    play(() => {
      tone(150, 0, 0.16, 'sine', 0.3, 60)
      tone(90, 0.01, 0.12, 'triangle', 0.12, 50)
    }),
  fanfare: () =>
    play(() => {
      ;[C5, E5, G5].forEach((f, i) => tone(f, i * 0.14, 0.22, 'triangle', 0.15))
      tone(C6, 0.42, 0.7, 'triangle', 0.18)
      tone(G5, 0.42, 0.7, 'sine', 0.08)
    })
}
