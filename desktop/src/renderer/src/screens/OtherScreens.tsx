import { useContext } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { BookOpen, Cpu } from 'lucide-react'
import { api } from '@/api'
import { LangContext, useT } from '@/strings'

export function CheckIndexScreen() {
  const t = useT()
  const navigate = useNavigate()
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  return (
    <div className="mx-auto max-w-4xl px-10 py-10">
      <h1 className="font-display text-4xl font-bold text-ink">{t.navCheck}</h1>
      <div className="mt-8 grid grid-cols-3 gap-3">
        {learners?.map((l) => (
          <button
            key={l.id}
            onClick={() => navigate(`/check/${l.id}`)}
            className="cursor-pointer rounded-card bg-card px-5 py-4 text-left font-display text-xl font-bold text-ink ring-1 ring-line hover:ring-accent-light"
          >
            {l.display_name}
          </button>
        ))}
      </div>
    </div>
  )
}

export function BooksScreen() {
  const t = useT()
  return (
    <div className="mx-auto max-w-4xl px-10 py-10">
      <h1 className="font-display text-4xl font-bold text-ink">{t.booksTitle}</h1>
      <div className="mt-8 flex items-start gap-4 rounded-card bg-card p-6 ring-1 ring-line">
        <BookOpen className="size-8 shrink-0 text-accent" aria-hidden />
        <div>
          <p className="text-xs font-extrabold tracking-widest text-muted uppercase">{t.comingSoon}</p>
          <p className="mt-1 text-lg text-body">{t.booksSoon}</p>
        </div>
      </div>
    </div>
  )
}

const MODELS = [
  { name: 'Meta MMS forced aligner', role: 'Basa · Sanay', license: 'CC-BY-NC-4.0' },
  { name: 'Qwen 2.5 3B (Ollama)', role: 'Group plans', license: 'See model card' }
]

export function SettingsScreen() {
  const t = useT()
  const { lang, setLang } = useContext(LangContext)
  return (
    <div className="mx-auto max-w-3xl px-10 py-10">
      <h1 className="font-display text-4xl font-bold text-ink">{t.settingsTitle}</h1>
      <section className="mt-8 rounded-card bg-card p-6 ring-1 ring-line">
        <h2 className="font-bold text-ink">{t.language}</h2>
        <div className="mt-3 inline-flex rounded-xl bg-paper-2 p-1 ring-1 ring-line">
          {(['fil', 'en'] as const).map((l) => (
            <button
              key={l}
              onClick={() => setLang(l)}
              className={`cursor-pointer rounded-lg px-5 py-2 font-bold ${lang === l ? 'bg-ink text-paper' : 'text-ink'}`}
            >
              {l === 'fil' ? 'Filipino' : 'English'}
            </button>
          ))}
        </div>
      </section>
      <section className="mt-5 rounded-card bg-card p-6 ring-1 ring-line">
        <h2 className="flex items-center gap-2 font-bold text-ink">
          <Cpu className="size-5 text-correct" aria-hidden /> {t.modelsTitle}
        </h2>
        <ul className="mt-3 divide-y divide-line">
          {MODELS.map((m) => (
            <li key={m.name} className="flex items-center justify-between py-3">
              <div>
                <p className="font-bold text-ink">{m.name}</p>
                <p className="text-sm text-muted">{m.role}</p>
              </div>
              <span className="rounded-full bg-paper-2 px-3 py-1 text-xs font-bold text-ink">{m.license}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
