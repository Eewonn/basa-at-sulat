import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { ArrowLeft, Check, Mic, MicOff } from 'lucide-react'
import { api } from '@/api'
import { useRecorder } from '@/audio/useRecorder'
import { LiveWaveform } from '@/components/LiveWaveform'
import { Stamp } from '@/components/Stamp'
import { Tamaraw } from '@/components/Tamaraw'
import { markSetupDone } from '@/display'
import { useT } from '@/strings'

const FIELD = 'w-full rounded-tile bg-white px-4 py-3 text-lg font-bold text-navy ring-2 ring-line outline-none focus:ring-blue'

// First run: Taw introduces the app, the teacher names the class, and we test the microphone.
export function WelcomeScreen() {
  const t = useT()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const rec = useRecorder()
  const [step, setStep] = useState(0)
  const [micOk, setMicOk] = useState(false)
  const { data: cls } = useQuery({ queryKey: ['classSettings'], queryFn: () => api.classSettings() })
  const [teacher, setTeacher] = useState<string | null>(null)
  const [section, setSection] = useState<string | null>(null)
  const save = useMutation({
    mutationFn: () => api.saveClassSettings({ teacher_name: (teacher ?? cls?.teacher_name ?? '').trim(), section: (section ?? cls?.section ?? '').trim() }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['classSettings'] })
  })

  // The mic test passes once we hear something louder than room noise.
  useEffect(() => {
    const analyser = rec.analyser
    if (!analyser) return
    const buf = new Uint8Array(analyser.fftSize)
    let raf = 0
    const tick = () => {
      analyser.getByteTimeDomainData(buf)
      let sum = 0
      for (const v of buf) sum += ((v - 128) / 128) ** 2
      if (Math.sqrt(sum / buf.length) > 0.04) setMicOk(true)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [rec.analyser])

  const next = async () => {
    if (step === 1) save.mutate()
    if (step === 2 && rec.state === 'recording') await rec.stop()
    setStep((s) => s + 1)
  }
  const finish = () => {
    markSetupDone()
    navigate('/')
  }

  const bubble = [t.welcomeHi, t.welcomeClass, t.welcomeMic, t.welcomeDone][step]

  return (
    <div className="paper flex h-full items-center justify-center bg-kid px-10">
      <div className="flex w-full max-w-5xl items-center gap-12">
        <div className="flex w-72 shrink-0 flex-col items-center gap-3">
          <p key={bubble} className="relative animate-pop rounded-tile bg-white px-5 py-3 text-center font-hand text-3xl leading-tight text-navy shadow-soft">
            {bubble}
            <span className="absolute -bottom-2 left-1/2 size-4 -translate-x-1/2 rotate-45 bg-white" aria-hidden />
          </p>
          <Tamaraw mood={step === 0 || step === 3 ? 'happy' : step === 2 && rec.state === 'recording' ? 'listening' : 'idle'} size={230} dance={step === 3} />
        </div>

        <div key={step} className="min-w-0 flex-1 animate-page-in rounded-card bg-white p-10 shadow-lift">
          <div className="mb-6 flex gap-2" aria-hidden>
            {[0, 1, 2, 3].map((i) => (
              <span key={i} className={`h-2.5 w-12 rounded-full ${i < step ? 'bg-teal' : i === step ? 'bg-blue' : 'bg-blue-soft'}`} />
            ))}
          </div>

          {step === 0 && <p className="text-2xl leading-relaxed font-bold text-navy">{t.welcomeIntro}</p>}

          {step === 1 && (
            <div className="flex flex-col gap-4">
              <label className="flex flex-col gap-2">
                <span className="font-extrabold text-navy">{t.teacherName}</span>
                <input className={FIELD} value={teacher ?? cls?.teacher_name ?? ''} onChange={(e) => setTeacher(e.target.value)} />
              </label>
              <label className="flex flex-col gap-2">
                <span className="font-extrabold text-navy">{t.sectionName}</span>
                <input className={FIELD} value={section ?? cls?.section ?? ''} onChange={(e) => setSection(e.target.value)} />
              </label>
            </div>
          )}

          {step === 2 && (
            <div className="flex flex-col gap-4">
              <p className="text-xl font-bold text-body">{t.welcomeMicHint}</p>
              {rec.state === 'blocked' ? (
                <div className="flex items-start gap-3 rounded-card bg-coral-soft p-5 text-coral-ink">
                  <MicOff className="mt-0.5 size-6 shrink-0" aria-hidden />
                  <div>
                    <p className="font-extrabold">{t.micBlocked}</p>
                    <p className="mt-1 text-sm font-semibold">{window.basa?.platform === 'win32' ? t.micBlockedFixWin : t.micBlockedFixLinux}</p>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-5">
                  <button
                    onClick={() => (rec.state === 'recording' ? void rec.stop() : void rec.start())}
                    className={`grid size-20 shrink-0 cursor-pointer place-items-center rounded-full text-white shadow-soft ${rec.state === 'recording' ? 'animate-ring bg-coral' : 'bg-blue hover:bg-blue-dark'}`}
                    aria-label={t.micTest}
                  >
                    <Mic className="size-9" />
                  </button>
                  <div className="min-w-0 flex-1">
                    <LiveWaveform analyser={rec.analyser} color="#2D5BD3" height={72} />
                  </div>
                </div>
              )}
              {micOk && (
                <p className="flex animate-pop items-center gap-2 text-xl font-black text-teal-ink">
                  <Check className="size-6" strokeWidth={3} aria-hidden /> {t.micOk}
                </p>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="flex items-center gap-6">
              <Stamp size={150} />
              <p className="text-2xl leading-relaxed font-bold text-navy">{t.welcomeDoneText}</p>
            </div>
          )}

          <div className="mt-10 flex items-center justify-between">
            {step > 0 ? (
              <button onClick={() => setStep((s) => s - 1)} className="flex cursor-pointer items-center gap-2 font-extrabold text-blue hover:text-blue-dark">
                <ArrowLeft className="size-5" strokeWidth={3} aria-hidden /> {t.back}
              </button>
            ) : (
              <span />
            )}
            {step < 3 ? (
              <button onClick={next} className="cursor-pointer rounded-full bg-blue px-10 py-4 text-xl font-black text-white shadow-soft hover:bg-blue-dark">
                {t.next}
              </button>
            ) : (
              <button onClick={finish} className="cursor-pointer rounded-full bg-teal px-10 py-4 text-xl font-black text-white shadow-soft hover:brightness-105">
                {t.begin}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
