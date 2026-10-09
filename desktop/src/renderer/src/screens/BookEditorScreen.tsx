import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router'
import { ArrowLeft, Check, Loader2, Mic, Pause, Play, RotateCcw, Sparkles, Square } from 'lucide-react'
import { api } from '@/api'
import type { Book, Category } from '@/api/types'
import { useRecorder } from '@/audio/useRecorder'
import { KaraokeText } from '@/components/KaraokeText'
import { LiveWaveform } from '@/components/LiveWaveform'
import { Tamaraw } from '@/components/Tamaraw'
import { CategoryTile, useToast } from '@/components/ui'
import { useT } from '@/strings'
import { CATEGORY_EMOJI } from './CheckScreen'

type Step = 'write' | 'record' | 'preview'

const FIELD = 'w-full rounded-tile bg-white px-4 py-3 text-lg font-bold text-navy ring-2 ring-line outline-none focus:ring-blue'

// Sulat: type a story, record a fluent speaker reading it, preview with highlighting.
export function BookEditorScreen() {
  const t = useT()
  const toast = useToast()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const rec = useRecorder()
  const [step, setStep] = useState<Step>('write')
  const [title, setTitle] = useState('')
  const [language, setLanguage] = useState('Filipino')
  const [reader, setReader] = useState('')
  const [category, setCategory] = useState<Category>('bukid')
  const [text, setText] = useState('')
  // From a reading group's "make a book" button: the group's missed words become the AI's idea.
  const fromGroup = (useLocation().state as { words?: string[] } | null)?.words
  const [idea, setIdea] = useState(() => (fromGroup ? t.aiIdeaWords(fromGroup) : ''))
  const [elapsed, setElapsed] = useState(0)
  const [book, setBook] = useState<Book | null>(null)
  const [time, setTime] = useState(0)
  const [playing, setPlaying] = useState(false)
  const audio = useRef<HTMLAudioElement>(null)

  const create = useMutation({
    mutationFn: ({ blob, seconds }: { blob: Blob; seconds: number }) =>
      api.createBook({ title: title.trim(), language: language.trim(), category, text: text.trim(), reader: reader.trim() }, blob, seconds),
    onSuccess: (b) => {
      setBook(b)
      setStep('preview')
      qc.invalidateQueries({ queryKey: ['books'] })
      qc.invalidateQueries({ queryKey: ['passages'] })
    }
  })

  const draft = useMutation({
    mutationFn: () => api.draftStory(category, language, idea.trim()),
    onSuccess: (d) => {
      setTitle(d.title)
      setText(d.text)
    },
    onError: () => toast(t.aiDraftFailed)
  })

  const drafted = useRef(false)
  useEffect(() => {
    if (!fromGroup || drafted.current) return
    drafted.current = true
    draft.mutate()
  }, [fromGroup, draft])

  useEffect(() => {
    if (rec.state !== 'recording') return
    const started = Date.now()
    const id = setInterval(() => setElapsed((Date.now() - started) / 1000), 200)
    return () => clearInterval(id)
  }, [rec.state])

  useEffect(() => {
    if (!playing) return
    let raf = 0
    const tick = () => {
      setTime(audio.current?.currentTime ?? 0)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing])

  const toggleRecord = async () => {
    if (rec.state === 'recording') create.mutate({ blob: await rec.stop(), seconds: elapsed })
    else {
      setElapsed(0)
      await rec.start()
    }
  }

  const togglePlay = () => {
    if (!audio.current) return
    if (playing) audio.current.pause()
    else void audio.current.play()
    setPlaying(!playing)
  }

  const canContinue = title.trim() && text.trim() && language.trim() && reader.trim()
  const steps: [Step, string][] = [
    ['write', t.stepWrite],
    ['record', t.stepRecord],
    ['preview', t.stepPreview]
  ]
  const stepIndex = steps.findIndex(([s]) => s === step)

  return (
    <div className="w-full max-w-[1680px] px-10 py-10">
      <button onClick={() => navigate('/books')} className="flex cursor-pointer items-center gap-2 font-extrabold text-blue hover:text-blue-dark">
        <ArrowLeft className="size-5" strokeWidth={3} aria-hidden /> {t.booksTitle}
      </button>
      <h1 className="mt-3 text-[40px] leading-tight font-black text-navy">{t.newBook}</h1>

      <ol className="mt-5 flex items-center gap-3">
        {steps.map(([s, label], i) => (
          <li key={s} className="flex items-center gap-3">
            <span
              className={`flex items-center gap-2 rounded-full px-4 py-2 font-extrabold ${
                i < stepIndex ? 'bg-teal-soft text-teal-ink' : i === stepIndex ? 'bg-blue text-white' : 'bg-side text-muted'
              }`}
            >
              {i < stepIndex ? <Check className="size-4" strokeWidth={3} aria-hidden /> : <span>{i + 1}</span>}
              {label}
            </span>
            {i < steps.length - 1 && <span className="h-0.5 w-8 bg-line" aria-hidden />}
          </li>
        ))}
      </ol>

      {step === 'write' && (
        <div className="mt-8 grid max-w-6xl gap-6 lg:grid-cols-[1fr_1.4fr]">
          <div className="flex flex-col gap-5">
            <label className="flex flex-col gap-2">
              <span className="font-extrabold text-navy">{t.fieldTitle}</span>
              <input className={FIELD} value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>
            <label className="flex flex-col gap-2">
              <span className="font-extrabold text-navy">{t.fieldLanguage}</span>
              <input className={FIELD} value={language} onChange={(e) => setLanguage(e.target.value)} placeholder={t.fieldLanguageHint} />
            </label>
            <label className="flex flex-col gap-2">
              <span className="font-extrabold text-navy">{t.fieldReader}</span>
              <input className={FIELD} value={reader} onChange={(e) => setReader(e.target.value)} placeholder={t.fieldReaderHint} />
            </label>
            <div className="flex flex-col gap-2">
              <span className="font-extrabold text-navy">{t.fieldCategory}</span>
              <div className="flex flex-wrap gap-3">
                {(Object.keys(CATEGORY_EMOJI) as Category[]).map((c) => (
                  <CategoryTile key={c} label={t.cat[c]} emoji={CATEGORY_EMOJI[c]} selected={category === c} onClick={() => setCategory(c)} />
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-3 rounded-card bg-blue-soft/50 p-5 ring-1 ring-blue/20">
              <label className="flex flex-col gap-2">
                <span className="font-extrabold text-navy">{t.aiIdea}</span>
                <input className={FIELD} value={idea} onChange={(e) => setIdea(e.target.value)} placeholder={t.aiIdeaHint} />
              </label>
              <button
                disabled={draft.isPending}
                onClick={() => draft.mutate()}
                className="flex cursor-pointer items-center gap-2 self-start rounded-full bg-blue px-6 py-3 font-black text-white transition hover:bg-blue-dark disabled:cursor-wait disabled:opacity-60"
              >
                {draft.isPending ? <Loader2 className="size-5 animate-spin" aria-hidden /> : <Sparkles className="size-5" aria-hidden />}
                {draft.isPending ? t.aiDrafting : t.aiDraft}
              </button>
              <p className="text-sm font-semibold text-body">{t.aiDraftNote}</p>
            </div>
          </div>
          <label className="flex flex-col gap-2">
            <span className="font-extrabold text-navy">{t.fieldStory}</span>
            <textarea className={`${FIELD} min-h-80 flex-1 resize-none text-2xl leading-relaxed`} value={text} onChange={(e) => setText(e.target.value)} />
            <button
              disabled={!canContinue}
              onClick={() => setStep('record')}
              className="mt-2 cursor-pointer self-end rounded-full bg-blue px-8 py-3 text-lg font-black text-white transition hover:bg-blue-dark disabled:cursor-not-allowed disabled:opacity-40"
            >
              {t.nextStep}
            </button>
          </label>
        </div>
      )}

      {step === 'record' && create.isPending && (
        <div className="flex flex-col items-center gap-4 py-16">
          <Tamaraw mood="thinking" size={180} />
          <p className="text-2xl font-black text-navy">{t.aligning}</p>
        </div>
      )}

      {step === 'record' && !create.isPending && (
        <div className="mt-8 flex max-w-5xl flex-col gap-6">
          <div>
            <h2 className="text-2xl font-black text-navy">{t.recordModel}</h2>
            <p className="mt-1 font-semibold text-body">{t.recordModelHint}</p>
          </div>
          <p className="rounded-card bg-white p-8 text-[34px] leading-relaxed font-extrabold text-navy shadow-soft ring-1 ring-line">{text}</p>
          <div className="flex items-center gap-6">
            <button
              onClick={toggleRecord}
              className={`flex size-24 shrink-0 cursor-pointer items-center justify-center rounded-full text-white shadow-lift transition ${
                rec.state === 'recording' ? 'animate-ring bg-coral' : 'bg-blue hover:bg-blue-dark'
              }`}
              aria-label={rec.state === 'recording' ? t.recordStop : t.recordStart}
            >
              {rec.state === 'recording' ? <Square className="size-9 fill-current" /> : <Mic className="size-10" />}
            </button>
            <div className="min-w-0 flex-1">
              <LiveWaveform analyser={rec.analyser} color="#2D5BD3" />
              <p className="mt-2 text-sm font-extrabold text-navy tabular-nums">
                {rec.state === 'recording' ? `● ${elapsed.toFixed(1)} s` : t.recordStart}
              </p>
            </div>
          </div>
          {rec.state === 'blocked' && <p className="rounded-tile bg-coral-soft p-4 font-bold text-coral-ink">{t.micBlocked}</p>}
        </div>
      )}

      {step === 'preview' && book?.words && (
        <div className="mt-8 flex max-w-5xl flex-col gap-6">
          <p className="font-semibold text-body">{t.previewHint}</p>
          <div className="rounded-card bg-white p-8 shadow-soft ring-1 ring-line">
            <KaraokeText
              words={book.words}
              time={time}
              onSeek={(s) => {
                if (audio.current) audio.current.currentTime = s
                setTime(s)
              }}
            />
          </div>
          <audio ref={audio} src={book.audio_url} onEnded={() => setPlaying(false)} />
          <div className="flex flex-wrap gap-3">
            <button onClick={togglePlay} className="flex cursor-pointer items-center gap-2 rounded-full bg-blue px-8 py-4 text-xl font-black text-white hover:bg-blue-dark">
              {playing ? <Pause className="size-6 fill-current" /> : <Play className="size-6 fill-current" />}
              {playing ? t.pausePlayback : t.play}
            </button>
            <button
              onClick={() => {
                toast(t.savedBook)
                navigate(`/books/${book.id}`)
              }}
              className="flex cursor-pointer items-center gap-2 rounded-full bg-teal px-8 py-4 text-xl font-black text-white hover:brightness-105"
            >
              <Check className="size-6" strokeWidth={3} aria-hidden /> {t.saveBook}
            </button>
            <button
              onClick={() => setStep('record')}
              className="flex cursor-pointer items-center gap-2 rounded-full px-6 py-4 text-lg font-extrabold text-navy ring-2 ring-navy hover:bg-side"
            >
              <RotateCcw className="size-5" aria-hidden /> {t.reRecordBook}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
