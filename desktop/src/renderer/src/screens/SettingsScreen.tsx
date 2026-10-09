import { useContext, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Cpu, FolderOpen, Info, Pencil, Shield, Type, Users } from 'lucide-react'
import { api } from '@/api'
import { Tamaraw } from '@/components/Tamaraw'
import { Avatar, useToast } from '@/components/ui'
import { applyTextSize, getTextSize, type TextSize } from '@/display'
import { LangContext, useT } from '@/strings'

const MODELS = [
  { name: 'Meta MMS forced aligner', role: 'Basa · Sanay · Sulat', license: 'CC-BY-NC-4.0' },
  { name: 'Qwen 2.5 3B (Ollama)', role: 'Group plans', license: 'See model card' }
]

function Card({ title, icon, children, wide = false }: { title: string; icon: ReactNode; children: ReactNode; wide?: boolean }) {
  return (
    <section className={`rounded-card bg-white p-6 shadow-soft ring-1 ring-line ${wide ? 'xl:col-span-2' : ''}`}>
      <h2 className="flex items-center gap-2 text-xl font-extrabold text-navy">
        {icon} {title}
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  )
}

function Segmented<T extends string>({ value, options, onChange }: { value: T; options: [T, string][]; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex rounded-full bg-side p-1">
      {options.map(([v, label]) => (
        <button key={v} onClick={() => onChange(v)} className={`cursor-pointer rounded-full px-6 py-2 font-extrabold ${value === v ? 'bg-blue text-white' : 'text-navy'}`}>
          {label}
        </button>
      ))}
    </div>
  )
}

export function SettingsScreen() {
  const t = useT()
  const toast = useToast()
  const qc = useQueryClient()
  const { lang, setLang } = useContext(LangContext)
  const [size, setSize] = useState<TextSize>(getTextSize)
  const [armed, setArmed] = useState(false)
  const [newName, setNewName] = useState('')
  const [editing, setEditing] = useState<{ id: string; name: string } | null>(null)
  const { data: storage } = useQuery({ queryKey: ['storage'], queryFn: () => api.storage() })
  const { data: learners } = useQuery({ queryKey: ['learners'], queryFn: () => api.learners() })

  const wipe = useMutation({
    mutationFn: () => api.deleteAllAudio(),
    onSuccess: ({ deleted }) => {
      setArmed(false)
      toast(t.deletedAudio(deleted))
      qc.invalidateQueries({ queryKey: ['storage'] })
    }
  })
  const add = useMutation({
    mutationFn: (name: string) => api.addLearner(name),
    onSuccess: () => {
      setNewName('')
      qc.invalidateQueries({ queryKey: ['learners'] })
    }
  })
  const rename = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => api.renameLearner(id, name),
    onSuccess: () => {
      setEditing(null)
      qc.invalidateQueries({ queryKey: ['learners'] })
    }
  })

  return (
    <div className="w-full max-w-[1680px] px-10 py-10">
      <h1 className="text-[40px] leading-tight font-black text-navy">{t.settingsTitle}</h1>
      <div className="mt-8 grid items-start gap-5 xl:grid-cols-2">
        <Card title={t.language} icon={<Info className="size-5 text-blue" aria-hidden />}>
          <Segmented value={lang} options={[['fil', 'Filipino'], ['en', 'English']]} onChange={setLang} />
        </Card>

        <Card title={t.secDisplay} icon={<Type className="size-5 text-blue" aria-hidden />}>
          <Segmented
            value={size}
            options={[
              ['normal', t.sizeNormal],
              ['large', t.sizeLarge]
            ]}
            onChange={(s) => {
              setSize(s)
              applyTextSize(s)
            }}
          />
        </Card>

        <Card title={t.secPrivacy} icon={<Shield className="size-5 text-teal-ink" aria-hidden />}>
          {storage && (
            <div className="space-y-3">
              <p className="text-lg font-extrabold text-navy">{t.audioStored(storage.audio_files, storage.audio_mb)}</p>
              <p className="flex items-center gap-2 font-semibold text-body">
                <FolderOpen className="size-4" aria-hidden /> {t.dataFolder}: <code className="rounded bg-side px-2 py-0.5 text-sm">{storage.data_dir}</code>
              </p>
              <button
                onClick={() => (armed ? wipe.mutate() : setArmed(true))}
                onBlur={() => setArmed(false)}
                disabled={wipe.isPending}
                className={`cursor-pointer rounded-full px-6 py-3 font-extrabold transition ${
                  armed ? 'bg-coral text-white' : 'text-coral-ink ring-2 ring-coral hover:bg-coral-soft'
                }`}
              >
                {armed ? t.deleteConfirm : t.deleteAudio}
              </button>
              <p className="text-sm font-semibold text-muted">{t.keepsBooks}</p>
            </div>
          )}
        </Card>

        <Card title={t.secClass} icon={<Users className="size-5 text-blue" aria-hidden />}>
          <ul className="max-h-64 divide-y divide-line overflow-y-auto">
            {learners?.map((l, i) => (
              <li key={l.id} className="flex items-center gap-3 py-2">
                <Avatar name={l.display_name} index={i} size={36} />
                {editing?.id === l.id ? (
                  <form
                    className="flex flex-1 gap-2"
                    onSubmit={(e) => {
                      e.preventDefault()
                      if (editing.name.trim()) rename.mutate({ id: l.id, name: editing.name.trim() })
                    }}
                  >
                    <input autoFocus className="flex-1 rounded-tile px-3 py-1.5 font-bold text-navy ring-2 ring-blue outline-none" value={editing.name} onChange={(e) => setEditing({ id: l.id, name: e.target.value })} />
                    <button className="cursor-pointer rounded-full bg-blue px-4 font-extrabold text-white">{t.save}</button>
                    <button type="button" onClick={() => setEditing(null)} className="cursor-pointer px-2 font-bold text-muted">
                      {t.cancel}
                    </button>
                  </form>
                ) : (
                  <>
                    <span className="flex-1 font-extrabold text-navy">{l.display_name}</span>
                    <button onClick={() => setEditing({ id: l.id, name: l.display_name })} aria-label={t.rename} title={t.rename} className="cursor-pointer rounded-full p-2 text-blue hover:bg-blue-soft">
                      <Pencil className="size-4" />
                    </button>
                  </>
                )}
              </li>
            ))}
          </ul>
          <form
            className="mt-3 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              if (newName.trim()) add.mutate(newName.trim())
            }}
          >
            <input
              className="flex-1 rounded-tile bg-white px-4 py-2.5 font-bold text-navy ring-2 ring-line outline-none focus:ring-blue"
              placeholder={t.learnerNamePh}
              aria-label={t.addLearner}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <button disabled={!newName.trim()} className="cursor-pointer rounded-full bg-blue px-6 font-extrabold text-white disabled:opacity-40">
              {t.add}
            </button>
          </form>
        </Card>

        <Card title={t.modelsTitle} icon={<Cpu className="size-5 text-teal-ink" aria-hidden />}>
          <ul className="divide-y divide-line">
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
        </Card>

        <Card title={t.secAbout} icon={<Info className="size-5 text-blue" aria-hidden />}>
          <div className="flex items-center gap-4">
            <Tamaraw size={72} />
            <div className="space-y-1">
              <p className="font-extrabold text-navy">
                {t.appName} · {t.version} 0.1.0
              </p>
              <p className="font-semibold text-body">{t.aboutOffline}</p>
              <p className="text-sm font-semibold text-muted">{t.creditsText}</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
