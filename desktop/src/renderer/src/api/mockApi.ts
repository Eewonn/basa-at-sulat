import type { Api, Assessment, Learner, Passage, PracticeItem, Word, WordLabel } from './types'

// Sample data only: synthetic learners, team-written passages (same as data/passages/passages.json).
const PASSAGES: Passage[] = [
  {
    id: 'fil_g2_01',
    title: 'Ang Palay ni Lina',
    language: 'fil',
    grade: 2,
    text: 'Nagtanim si Lina ng palay sa bukid. Masaya siya. Tinulungan siya ng kanyang lolo. Pagkatapos, kumain sila ng mangga sa ilalim ng puno.'
  },
  {
    id: 'eng_g2_01',
    title: "Ben's Red Kite",
    language: 'eng',
    grade: 2,
    text: 'Ben has a red kite. He runs to the hill with his sister. The wind is strong, and the kite flies high. They laugh and wave at the birds.'
  }
]

const LEARNERS: Learner[] = [
  { id: 'l_01', display_name: 'Lina', grade: 2, level: 'Developing', last_check: '2026-10-02', needs_practice: true },
  { id: 'l_02', display_name: 'Paolo', grade: 2, level: 'Transitioning', last_check: '2026-10-02' },
  { id: 'l_03', display_name: 'Mika', grade: 2, level: 'Grade level', last_check: '2026-10-01' },
  { id: 'l_04', display_name: 'Josie', grade: 2, level: 'Emerging', last_check: '2026-09-30', needs_practice: true },
  { id: 'l_05', display_name: 'Ramon', grade: 2, level: 'Developing', last_check: '2026-09-30', needs_practice: true },
  { id: 'l_06', display_name: 'Ana', grade: 2 }
]

// Planted results per passage: which words come back flagged, and what was "heard".
const PLANTED: Record<string, { i: number; label: WordLabel; heard?: string }[]> = {
  fil_g2_01: [
    { i: 3, label: 'skipped' },
    { i: 4, label: 'misread', heard: 'pala' }
  ],
  eng_g2_01: [
    { i: 4, label: 'misread', heard: 'kit' },
    { i: 11, label: 'skipped' }
  ]
}

export function levelFor(wcpm: number): string {
  if (wcpm < 30) return 'Emerging'
  if (wcpm < 55) return 'Developing'
  if (wcpm < 75) return 'Transitioning'
  return 'Grade level'
}

function recompute(a: Assessment): Assessment {
  const correct = a.words.filter((w) => w.label === 'matched').length
  const wcpm = Math.round((correct / a.duration_sec) * 60)
  return { ...a, wcpm, level: levelFor(wcpm) }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))
const store = new Map<string, Assessment>()
let seq = 0

function buildAssessment(learnerId: string, passage: Passage): Assessment {
  const planted = PLANTED[passage.id] ?? []
  let t = 0.4
  const words: Word[] = passage.text.split(/\s+/).map((text, i) => {
    const p = planted.find((x) => x.i === i)
    const len = p?.label === 'skipped' ? 0.04 : 0.25 + text.length * 0.07
    const w: Word = {
      i,
      text,
      label: p?.label ?? 'matched',
      score: p?.label === 'skipped' ? 0.08 : p?.label === 'misread' ? 0.31 : 0.86 + (i % 5) * 0.02,
      start: +t.toFixed(2),
      end: +(t + len).toFixed(2),
      heard: p?.heard
    }
    t += len + (i === 2 ? 1.8 : 0.12)
    return w
  })
  return recompute({
    assessment_id: `a_${++seq}`,
    learner_id: learnerId,
    passage_id: passage.id,
    duration_sec: +t.toFixed(1),
    words,
    pauses: passage.id === 'fil_g2_01' ? [{ before_word: 3, seconds: 1.8 }] : [],
    wcpm: 0,
    level: '',
    status: 'draft',
    timings: { convert_ms: 180, align_ms: 1650, score_ms: 240 }
  })
}

const practiceTries = new Map<string, number>()

export const mockApi: Api = {
  mode: 'mock',
  async health() {
    await sleep(150)
    return { ok: true, models: { aligner: 'loaded', ollama: 'up' } }
  },
  async learners() {
    await sleep(250)
    return LEARNERS
  },
  async passages() {
    await sleep(200)
    return PASSAGES
  },
  async assess(_audio, learnerId, passageId) {
    await sleep(2100)
    const passage = PASSAGES.find((p) => p.id === passageId) ?? PASSAGES[0]
    const a = buildAssessment(learnerId, passage)
    store.set(a.assessment_id, a)
    return a
  },
  async overrideWord(id, i, label) {
    const a = store.get(id)
    if (!a) throw new Error('Assessment not found')
    const next = recompute({ ...a, words: a.words.map((w) => (w.i === i ? { ...w, label } : w)) })
    store.set(id, next)
    return next
  },
  async confirm(id) {
    await sleep(300)
    const a = store.get(id)
    if (!a) throw new Error('Assessment not found')
    const next = { ...a, status: 'confirmed' as const }
    store.set(id, next)
    return next
  },
  async practice(learnerId) {
    const latest = [...store.values()].reverse().find((a) => a.learner_id === learnerId)
    const passage = PASSAGES.find((p) => p.id === latest?.passage_id) ?? PASSAGES[0]
    const sentences = passage.text.match(/[^.]+\./g) ?? [passage.text]
    const missed = latest
      ? latest.words.filter((w) => w.label !== 'matched')
      : buildAssessment(learnerId, passage).words.filter((w) => w.label !== 'matched')
    return missed.map<PracticeItem>((w) => ({
      word: w.text.replace(/[.,]/g, ''),
      sentence: (sentences.find((s) => s.includes(w.text.replace(/[.,]/g, ''))) ?? passage.text).trim()
    }))
  },
  async checkWord(_audio, word) {
    // Scripted for the mockup: first try misses, second try matches.
    await sleep(900)
    const tries = (practiceTries.get(word) ?? 0) + 1
    practiceTries.set(word, tries)
    return { result: tries >= 2 ? 'match' : 'no_match' }
  }
}
