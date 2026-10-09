import type { Api, Assessment, Book, BookWord, Category, ClassGroup, ClassSettings, PracticeItem, Progress } from './types'

// The engine stores ISO 639 codes (fil, eng, ilo…), but the book editor takes the language's name.
const LANGUAGE_CODES: Record<string, string> = {
  filipino: 'fil',
  tagalog: 'fil',
  english: 'eng',
  ilocano: 'ilo',
  ilokano: 'ilo',
  cebuano: 'ceb',
  hiligaynon: 'hil',
  kapampangan: 'pam',
  waray: 'war'
}

// An unknown name goes through as typed, and the engine's 422 says what it expects.
function languageCode(name: string): string {
  const key = name.trim().toLowerCase()
  return LANGUAGE_CODES[key] ?? key
}

// A FastAPI app answers an unknown route with exactly this; a real 404 (unknown learner, book…) says what's missing.
class RouteMissing extends Error {}

// What the engine doesn't store yet (docs/API.md "Proposed by frontend") is kept on this laptop until it does.
function local<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key)
    return v ? { ...fallback, ...JSON.parse(v) } : fallback
  } catch {
    return fallback
  }
}
function saveLocal(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Private storage can refuse writes; the setting just won't survive a restart.
  }
}
type BookMeta = { category?: Category; reader?: string; duration_sec?: number }
const bookMeta = () => local<Record<string, BookMeta>>('basa.bookMeta', {})

// Talks to the local engine (docs/API.md). Only ever 127.0.0.1: nothing leaves the laptop.
export function createHttpApi(port: number): Api {
  const base = `http://127.0.0.1:${port}`

  // Every engine book has its model reading (POST /books requires the audio), so it always has audio to play.
  // The category, reader and length the teacher entered are kept locally, since the engine doesn't store them yet.
  const withAudio = <T extends { id: string }>(b: T) => ({ ...bookMeta()[b.id], ...b, has_recording: true, audio_url: `${base}/books/${b.id}/audio` })

  async function json<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(base + path, init)
    if (!res.ok) {
      const body = await res.text()
      if (res.status === 404 && body === '{"detail":"Not Found"}') throw new RouteMissing(path)
      throw new Error(`${res.status} ${body}`)
    }
    return res.json() as Promise<T>
  }

  // For proposed routes: use the engine once it has the route, until then the fallback.
  async function orElse<T>(call: Promise<T>, fallback: () => T | Promise<T>): Promise<T> {
    try {
      return await call
    } catch (e) {
      if (e instanceof RouteMissing) return fallback()
      throw e
    }
  }

  const CLASS_KEY = 'basa.classSettings'
  const noClassSettings: ClassSettings = { teacher_name: '', section: '', grade: 0 }

  function form(fields: Record<string, string | Blob>): FormData {
    const f = new FormData()
    for (const [k, v] of Object.entries(fields)) f.append(k, v)
    return f
  }

  const api: Api = {
    health: () => json('/health'),
    learners: () => json('/learners'),
    passages: () => json('/passages'),
    assess: (audio, learnerId, passageId) =>
      json<Assessment>('/assess', {
        method: 'POST',
        body: form({ audio, learner_id: learnerId, passage_id: passageId })
      }),
    overrideWord: (id, i, label) =>
      json<Assessment>(`/assessments/${id}/words/${i}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label })
      }),
    confirm: (id) => json<Assessment>(`/assessments/${id}/confirm`, { method: 'POST' }),
    learnerStats: (learnerId) => json(`/learners/${learnerId}/stats`),
    practice: async (learnerId) => (await json<{ items: PracticeItem[] }>(`/learners/${learnerId}/practice`)).items,
    clipUrl: (bookId, wordIndex) => `${base}/books/${bookId}/clips/${wordIndex}`,
    progress: (learnerId) => json<Progress>(`/learners/${learnerId}/progress`),
    checkWord: (audio, word, learnerId) =>
      json('/practice/check', { method: 'POST', body: form({ audio, word, learner_id: learnerId }) }),
    recentChecks: () => json('/assessments/recent'),
    books: async () => (await json<Book[]>('/books')).map(withAudio),
    book: async (id) => withAudio(await json<Book>(`/books/${id}`)),
    createBook: async (book, audio, durationSec) => {
      // The engine replies with only {id, words}; the rest of the book is what the teacher just entered.
      const created = await json<{ id: string; words: BookWord[] }>('/books', {
        method: 'POST',
        body: form({ title: book.title, language: languageCode(book.language), text: book.text, audio })
      })
      saveLocal('basa.bookMeta', { ...bookMeta(), [created.id]: { category: book.category, reader: book.reader, duration_sec: durationSec } })
      return withAudio({ ...book, ...created, duration_sec: durationSec })
    },
    deleteBook: async (id) => {
      const res = await fetch(`${base}/books/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
      const { [id]: _, ...rest } = bookMeta()
      saveLocal('basa.bookMeta', rest)
    },
    classGroups: async (refresh) => (await json<{ groups: ClassGroup[] }>(`/class${refresh ? '?refresh=1' : ''}`)).groups,
    exportCsv: async () => {
      const res = await fetch(`${base}/class/export.csv`)
      if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
      return res.blob()
    },
    storage: () => orElse(json('/storage'), () => null),
    deleteAllAudio: () => json('/audio', { method: 'DELETE' }),
    addLearner: (name) =>
      json('/learners', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_name: name }) }),
    classSettings: () => orElse(json('/class/settings'), () => local(CLASS_KEY, noClassSettings)),
    saveClassSettings: (settings) =>
      orElse(json('/class/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings) }), () => {
        const next = { ...local(CLASS_KEY, noClassSettings), ...settings }
        saveLocal(CLASS_KEY, next)
        return next
      }),
    renameLearner: (id, name) =>
      json(`/learners/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_name: name }) })
  }
  return api
}
