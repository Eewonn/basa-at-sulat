import type { CSSProperties } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { Plus } from 'lucide-react'
import { api } from '@/api'
import type { Category } from '@/api/types'
import { Emoji } from '@/components/Emoji'
import { Tamaraw } from '@/components/Tamaraw'
import { useT } from '@/strings'
import { CATEGORY_EMOJI } from './CheckScreen'

export const COVER: Record<Category, string> = {
  bukid: 'bg-sun-soft',
  pamilya: 'bg-coral-soft',
  hayop: 'bg-banig-soft',
  kalikasan: 'bg-teal-soft',
  paaralan: 'bg-blue-soft'
}

// The Sulat library: read-along books made by the teacher and the community.
export function BooksScreen() {
  const t = useT()
  const navigate = useNavigate()
  const { data: books, isLoading } = useQuery({ queryKey: ['books'], queryFn: () => api.books() })

  return (
    <div className="w-full max-w-[1680px] px-10 py-10">
      <h1 className="text-[40px] leading-tight font-black text-navy">{t.booksTitle}</h1>
      <p className="mt-1 font-semibold text-body">{t.booksSubtitle}</p>

      <div className="mt-8 grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-6">
        <button
          onClick={() => navigate('/books/new')}
          className="stagger flex min-h-80 cursor-pointer flex-col items-center justify-center gap-3 rounded-card border-3 border-dashed border-blue/40 bg-blue-soft/50 p-6 text-center transition hover:-translate-y-1 hover:border-blue"
        >
          <span className="grid size-16 place-items-center rounded-full bg-blue text-white">
            <Plus className="size-8" strokeWidth={3} aria-hidden />
          </span>
          <p className="text-xl font-black text-navy">{t.newBook}</p>
          <p className="font-semibold text-body">{t.newBookHint}</p>
          <Tamaraw size={80} />
        </button>

        {isLoading && Array.from({ length: 3 }, (_, i) => <div key={i} className="shimmer min-h-80 rounded-card" />)}

        {books?.map((b, i) => (
          <button
            key={b.id}
            style={{ '--i': i + 1 } as CSSProperties}
            onClick={() => navigate(`/books/${b.id}`)}
            className="stagger flex min-h-80 cursor-pointer flex-col overflow-hidden rounded-card bg-white text-left shadow-soft ring-1 ring-line transition hover:-translate-y-1 hover:shadow-lift"
          >
            <div className={`grid h-40 place-items-center ${COVER[b.category]}`}>
              <Emoji name={CATEGORY_EMOJI[b.category]} size={88} />
            </div>
            <div className="flex flex-1 flex-col gap-2 p-5">
              <p className="text-xs font-extrabold tracking-wider text-muted uppercase">
                {b.language === 'fil' ? 'Filipino' : b.language === 'eng' ? 'English' : b.language} · {t.cat[b.category]}
              </p>
              <p className="text-xl leading-tight font-black text-navy">{b.title}</p>
              <span
                className={`mt-auto self-start rounded-full px-3 py-1 text-xs font-extrabold ${
                  b.has_recording ? 'bg-teal-soft text-teal-ink' : 'bg-sun-soft text-[#6b4f00]'
                }`}
              >
                {b.has_recording ? `${t.hasRecording}${b.reader ? ` · ${b.reader}` : ''}` : t.noRecording}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
