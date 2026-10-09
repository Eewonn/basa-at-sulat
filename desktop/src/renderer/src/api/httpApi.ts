import type { Api, Assessment, Book, BookWord } from './types'

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

// Talks to the local engine (docs/API.md). Only ever 127.0.0.1: nothing leaves the laptop.
export function createHttpApi(port: number): Api {
  const base = `http://127.0.0.1:${port}`

  // Every engine book has its model reading (POST /books requires the audio), so it always has audio to play.
  const withAudio = <T extends { id: string }>(b: T) => ({ ...b, has_recording: true, audio_url: `${base}/books/${b.id}/audio` })

  async function json<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(base + path, init)
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
    return res.json() as Promise<T>
  }

  function form(fields: Record<string, string | Blob>): FormData {
    const f = new FormData()
    for (const [k, v] of Object.entries(fields)) f.append(k, v)
    return f
  }

  return {
    mode: 'engine',
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
    practice: async (learnerId) =>
      (await json<{ items: { word: string; sentence: string }[] }>(`/learners/${learnerId}/practice`)).items,
    checkWord: (audio, word, learnerId) =>
      json('/practice/check', { method: 'POST', body: form({ audio, word, learner_id: learnerId }) }),
    recentChecks: () => json('/assessments/recent'),
    books: () => json('/books'),
    book: async (id) => withAudio(await json<Book>(`/books/${id}`)),
    createBook: async (book, audio, durationSec) => {
      // The engine replies with only {id, words}; the rest of the book is what the teacher just entered.
      const created = await json<{ id: string; words: BookWord[] }>('/books', {
        method: 'POST',
        body: form({ title: book.title, language: languageCode(book.language), text: book.text, audio })
      })
      return withAudio({ ...book, ...created, duration_sec: durationSec })
    },
    storage: () => json('/storage'),
    deleteAllAudio: () => json('/audio', { method: 'DELETE' }),
    addLearner: (name) =>
      json('/learners', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_name: name }) }),
    classSettings: () => json('/class/settings'),
    saveClassSettings: (settings) =>
      json('/class/settings', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings) }),
    renameLearner: (id, name) =>
      json(`/learners/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_name: name }) })
  }
}
