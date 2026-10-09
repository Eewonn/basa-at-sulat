import { useCallback, useEffect, useRef, useState } from 'react'

type RecorderState = 'idle' | 'recording' | 'blocked'

// Records the mic with MediaRecorder (webm/opus) and exposes a live analyser for the waveform.
// Works the same on Windows and Linux because Electron ships the same Chromium everywhere.
export function useRecorder() {
  const [state, setState] = useState<RecorderState>('idle')
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const stream = useRef<MediaStream | null>(null)
  const ctx = useRef<AudioContext | null>(null)
  const resolveStop = useRef<((b: Blob) => void) | null>(null)

  const cleanup = useCallback(() => {
    stream.current?.getTracks().forEach((t) => t.stop())
    ctx.current?.close()
    stream.current = null
    ctx.current = null
    setAnalyser(null)
  }, [])

  useEffect(() => cleanup, [cleanup])

  const start = useCallback(async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
      })
      stream.current = s
      ctx.current = new AudioContext()
      const node = ctx.current.createAnalyser()
      node.fftSize = 1024
      ctx.current.createMediaStreamSource(s).connect(node)
      setAnalyser(node)

      chunks.current = []
      const r = new MediaRecorder(s, { mimeType: 'audio/webm;codecs=opus' })
      r.ondataavailable = (e) => e.data.size > 0 && chunks.current.push(e.data)
      r.onstop = () => {
        resolveStop.current?.(new Blob(chunks.current, { type: 'audio/webm' }))
        cleanup()
      }
      recorder.current = r
      r.start()
      setState('recording')
    } catch {
      cleanup()
      setState('blocked')
    }
  }, [cleanup])

  const stop = useCallback(
    () =>
      new Promise<Blob>((resolve) => {
        resolveStop.current = resolve
        recorder.current?.stop()
        setState('idle')
      }),
    []
  )

  return { state, analyser, start, stop }
}
