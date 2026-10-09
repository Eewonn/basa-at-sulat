import type { Api, Assessment } from './types'

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
    practice: async (learnerId) =>
      (await json<{ items: { word: string; sentence: string }[] }>(`/learners/${learnerId}/practice`)).items,
    checkWord: (audio, word) => json('/practice/check', { method: 'POST', body: form({ audio, word }) })
  }
}
