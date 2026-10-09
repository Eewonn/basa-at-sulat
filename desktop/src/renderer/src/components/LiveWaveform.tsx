import { useEffect, useRef } from 'react'

// Scrolling bar waveform from the live mic. Pure Web Audio, no AI involved.
export function LiveWaveform({ analyser, color = '#B4521A', height = 96 }: { analyser: AnalyserNode | null; color?: string; height?: number }) {
  const canvas = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const el = canvas.current
    if (!el) return
    const g = el.getContext('2d')
    if (!g) return
    const dpr = window.devicePixelRatio || 1
    el.width = el.clientWidth * dpr
    el.height = height * dpr
    g.scale(dpr, dpr)

    const bar = 5
    const gap = 4
    const count = Math.floor(el.clientWidth / (bar + gap))
    const levels: number[] = new Array(count).fill(0.04)
    const buf = new Uint8Array(analyser?.fftSize ?? 1024)
    let raf = 0

    const draw = () => {
      if (analyser) {
        analyser.getByteTimeDomainData(buf)
        let sum = 0
        for (const v of buf) sum += ((v - 128) / 128) ** 2
        levels.push(Math.min(1, Math.sqrt(sum / buf.length) * 4))
        levels.shift()
      }
      g.clearRect(0, 0, el.clientWidth, height)
      g.fillStyle = color
      levels.forEach((lv, i) => {
        const h = Math.max(4, lv * (height - 8))
        g.beginPath()
        g.roundRect(i * (bar + gap), (height - h) / 2, bar, h, 3)
        g.fill()
      })
      raf = requestAnimationFrame(draw)
    }
    draw()
    return () => cancelAnimationFrame(raf)
  }, [analyser, color, height])

  return <canvas ref={canvas} className="w-full" style={{ height }} aria-hidden />
}
