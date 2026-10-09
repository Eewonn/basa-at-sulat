import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { ArrowLeft, Mic, Pause, Play, RotateCcw } from 'lucide-react'
import { api } from '@/api'
import { Emoji } from '@/components/Emoji'
import { KaraokeText } from '@/components/KaraokeText'
import { useT } from '@/strings'
import { CATEGORY_EMOJI } from './CheckScreen'
import { COVER } from './BooksScreen'

// Plays a book with word highlighting that follows its model reading.
export function BookPlayerScreen() {
  const t = useT()
  const navigate = useNavigate()
  const { bookId = '' } = useParams()
  const { data: book } = useQuery({ queryKey: ['book', bookId], queryFn: () => api.book(bookId) })
  const [playing, setPlaying] = useState(false)
  const [time, setTime] = useState(0)
  const audio = useRef<HTMLAudioElement>(null)

  // The highlight follows the real model reading's playback position.
  useEffect(() => {
    if (!playing) return
    let raf = 0
    const tick = () => {
      if (audio.current) setTime(audio.current.currentTime)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing])

  if (!book) return null

  const toggle = () => {
    if (!audio.current) return
    if (playing) audio.current.pause()
    else void audio.current.play()
    setPlaying(!playing)
  }
  const seek = (s: number) => {
    if (audio.current) audio.current.currentTime = s
    setTime(s)
  }

  return (
    <div className="w-full max-w-[1680px] px-10 py-10">
      <button onClick={() => navigate('/books')} className="flex cursor-pointer items-center gap-2 font-extrabold text-blue hover:text-blue-dark">
        <ArrowLeft className="size-5" strokeWidth={3} aria-hidden /> {t.booksTitle}
      </button>
      <div className="mt-4 flex items-center gap-5">
        <span className={`grid size-24 shrink-0 place-items-center rounded-card ${book.category ? COVER[book.category] : 'bg-side'}`}>
          <Emoji name={book.category ? CATEGORY_EMOJI[book.category] : 'books'} size={64} />
        </span>
        <div>
          <h1 className="text-[40px] leading-tight font-black text-navy">{book.title}</h1>
          <p className="font-semibold text-body">
            {[book.category && t.cat[book.category], book.reader && t.readBy(book.reader)].filter(Boolean).join(' · ')}
          </p>
        </div>
      </div>

      <div className="mt-8 max-w-5xl rounded-card bg-white p-8 shadow-soft ring-1 ring-line">
        {book.words ? <KaraokeText words={book.words} time={time} onSeek={seek} /> : <p className="text-[34px] leading-snug font-extrabold text-navy">{book.text}</p>}
      </div>

      {book.audio_url && <audio ref={audio} src={book.audio_url} onEnded={() => setPlaying(false)} />}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        {book.audio_url && (
          <>
            <button
              onClick={toggle}
              className="flex cursor-pointer items-center gap-2 rounded-full bg-blue px-8 py-4 text-xl font-black text-white shadow-soft transition hover:bg-blue-dark"
            >
              {playing ? <Pause className="size-6 fill-current" /> : <Play className="size-6 fill-current" />}
              {playing ? t.pausePlayback : t.play}
            </button>
            <button
              onClick={() => seek(0)}
              className="flex cursor-pointer items-center gap-2 rounded-full px-6 py-4 text-lg font-extrabold text-navy ring-2 ring-navy transition hover:bg-side"
            >
              <RotateCcw className="size-5" aria-hidden /> {t.restart}
            </button>
          </>
        )}
        <button
          onClick={() => navigate('/check')}
          className="flex cursor-pointer items-center gap-2 rounded-full px-6 py-4 text-lg font-extrabold text-purple ring-2 ring-purple transition hover:bg-[#f1eaff]"
        >
          <Mic className="size-5" aria-hidden /> {t.useInBasa}
        </button>
        {!book.audio_url && <span className="rounded-full bg-sun-soft px-3 py-1 text-sm font-extrabold text-[#6b4f00]">{t.noRecording}</span>}
      </div>
    </div>
  )
}
