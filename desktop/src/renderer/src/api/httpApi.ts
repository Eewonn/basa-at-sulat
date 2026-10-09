import type { Api, Assessment, Book } from './types'

// Talks to the local engine (docs/API.md). Only ever 127.0.0.1: nothing leaves the laptop.
export function createHttpApi(port: number): Api {
  const base = `http://127.0.0.1:${port}`

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
    book: async (id) => {
      const b = await json<Book>(`/books/${id}`)
      return b.has_recording ? { ...b, audio_url: `${base}/books/${id}/audio` } : b
    },
    createBook: (book, audio) => json('/books', { method: 'POST', body: form({ ...book, audio }) }),
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
