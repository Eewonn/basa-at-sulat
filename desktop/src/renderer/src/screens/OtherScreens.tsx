import { useContext } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { Cpu } from 'lucide-react'
import { api } from '@/api'
import { Emoji } from '@/components/Emoji'
import { Tamaraw } from '@/components/Tamaraw'
import { Avatar } from '@/components/ui'
import { LangContext, useT } from '@/strings'

export function CheckIndexScreen() {
  const t = useT()
  const navigate = useNavigate()
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })
  return (
    <div className="w-full max-w-[1680px] px-10 py-10">
      <h1 className="text-[40px] leading-tight font-black text-navy">{t.navCheck}</h1>
      <div className="mt-8 grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4">
        {learners?.map((l, i) => (
          <button
            key={l.id}
            onClick={() => navigate(`/check/${l.id}`)}
            className="flex cursor-pointer items-center gap-3 rounded-card bg-white p-4 text-left shadow-soft ring-1 ring-line transition hover:-translate-y-1"
          >
            <Avatar name={l.display_name} index={i} size={48} />
            <span className="text-xl font-black text-navy">{l.display_name}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export function BooksScreen() {
  const t = useT()
  return (
    <div className="w-full max-w-[1680px] px-10 py-10">
      <h1 className="text-[40px] leading-tight font-black text-navy">{t.booksTitle}</h1>
      <div className="mt-8 flex items-center gap-6 rounded-card bg-blue-soft p-8">
        <Emoji name="books" size={96} />
        <div className="flex-1">
          <p className="text-xs font-black tracking-widest text-blue uppercase">{t.comingSoon}</p>
          <p className="mt-1 text-xl font-bold text-navy">{t.booksSoon}</p>
        </div>
        <Tamaraw size={120} />
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
    <div className="w-full max-w-[1680px] px-10 py-10">
      <h1 className="text-[40px] leading-tight font-black text-navy">{t.settingsTitle}</h1>
      <div className="mt-8 grid items-start gap-5 xl:grid-cols-2">
      <section className="rounded-card bg-white p-6 shadow-soft ring-1 ring-line">
        <h2 className="text-xl font-extrabold text-navy">{t.language}</h2>
        <div className="mt-3 inline-flex rounded-full bg-side p-1">
          {(['fil', 'en'] as const).map((l) => (
            <button
              key={l}
              onClick={() => setLang(l)}
              className={`cursor-pointer rounded-full px-6 py-2 font-extrabold ${lang === l ? 'bg-blue text-white' : 'text-navy'}`}
            >
              {l === 'fil' ? 'Filipino' : 'English'}
            </button>
          ))}
        </div>
      </section>
      <section className="rounded-card bg-white p-6 shadow-soft ring-1 ring-line">
        <h2 className="flex items-center gap-2 text-xl font-extrabold text-navy">
          <Cpu className="size-5 text-teal-ink" aria-hidden /> {t.modelsTitle}
        </h2>
        <ul className="mt-3 divide-y divide-line">
          {MODELS.map((m) => (
            <li key={m.name} className="flex items-center justify-between py-3">
              <div>
                <p className="font-extrabold text-navy">{m.name}</p>
                <p className="text-sm font-semibold text-muted">{m.role}</p>
              </div>
              <span className="rounded-full bg-side px-3 py-1 text-xs font-extrabold text-navy">{m.license}</span>
            </li>
          ))}
        </ul>
      </section>
      </div>
      <section className="mt-5 flex items-center gap-4 rounded-card bg-white p-6 shadow-soft ring-1 ring-line">
        <Tamaraw size={72} />
        <div>
          <h2 className="text-xl font-extrabold text-navy">{t.creditsTitle}</h2>
          <p className="mt-1 font-semibold text-body">{t.creditsText}</p>
        </div>
      </section>
    </div>
  )
}
