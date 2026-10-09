import type { Api, Assessment, Learner, LearnerStats, Passage, PracticeItem, Word, WordLabel } from './types'

// Sample data only: synthetic learners, team-written passages (the first two match data/passages/passages.json).
const PASSAGES: Passage[] = [
  {
    id: 'fil_g2_01',
    title: 'Ang Palay ni Lina',
    language: 'fil',
    grade: 2,
    category: 'bukid',
    text: 'Nagtanim si Lina ng palay sa bukid. Masaya siya. Tinulungan siya ng kanyang lolo. Pagkatapos, kumain sila ng mangga sa ilalim ng puno.'
  },
  {
    id: 'eng_g2_01',
    title: "Ben's Red Kite",
    language: 'eng',
    grade: 2,
    category: 'kalikasan',
    text: 'Ben has a red kite. He runs to the hill with his sister. The wind is strong, and the kite flies high. They laugh and wave at the birds.'
  },
  {
    id: 'fil_g2_02',
    title: 'Ang Tamaraw',
    language: 'fil',
    grade: 2,
    category: 'hayop',
    text: 'Ang tamaraw ay nakatira sa Mindoro. Malakas at matapang ito. Kumakain ito ng damo sa bundok.'
  },
  {
    id: 'fil_g2_03',
    title: 'Tuwing Linggo',
    language: 'fil',
    grade: 2,
    category: 'pamilya',
    text: 'Tuwing Linggo, nagluluto si Nanay ng adobo. Naghuhugas naman ng plato si Tatay. Masaya ang buong pamilya.'
  },
  {
    id: 'fil_g2_04',
    title: 'Bagong Libro',
    language: 'fil',
    grade: 2,
    category: 'paaralan',
    text: 'Maagang pumasok si Ben sa paaralan. Binati niya ang kanyang guro. Nagbasa sila ng bagong libro.'
  },
  {
    id: 'eng_g2_02',
    title: 'The Quiet Garden',
    language: 'eng',
    grade: 2,
    category: 'kalikasan',
    text: 'The flowers are red and yellow. A small bee sits on a petal. The sun is warm, and the garden is quiet.'
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

const STATS: Record<string, LearnerStats> = {
  l_01: { stars: 12, streak_days: 3, minutes_read: 25, practicing: ['palay', 'ng', 'kanyang'], wcpm_history: series([41, 46, 44, 52, 58]) },
  l_02: { stars: 20, streak_days: 5, minutes_read: 41, practicing: ['Tinulungan'], wcpm_history: series([55, 60, 63, 66]) },
  l_03: { stars: 31, streak_days: 7, minutes_read: 64, practicing: [], wcpm_history: series([70, 74, 79, 82]) },
  l_04: { stars: 4, streak_days: 1, minutes_read: 9, practicing: ['Nagtanim', 'bukid', 'mangga'], wcpm_history: series([18, 22, 27]) },
  l_05: { stars: 9, streak_days: 2, minutes_read: 18, practicing: ['palay', 'Pagkatapos'], wcpm_history: series([38, 43, 49]) },
  l_06: { stars: 0, streak_days: 0, minutes_read: 0, practicing: [], wcpm_history: [] }
}

function series(values: number[]) {
  return values.map((wcpm, i) => ({ date: `2026-09-${String(8 + i * 6).padStart(2, '0')}`, wcpm }))
}

// Planted results: which words come back flagged, and what was "heard".
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
const DEFAULT_PLANTED = [
  { i: 4, label: 'misread' as const, heard: undefined },
  { i: 8, label: 'skipped' as const }
]

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
const clean = (w: string) => w.replace(/[.,]/g, '')

function buildAssessment(learnerId: string, passage: Passage): Assessment {
  const planted = PLANTED[passage.id] ?? DEFAULT_PLANTED
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
      heard: p?.label === 'misread' ? p.heard ?? clean(text).slice(0, -1) : undefined
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
    pauses: [{ before_word: 3, seconds: 1.8 }],
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
    return LEARNERS.map((l) => ({ ...l, stars: STATS[l.id]?.stars, streak_days: STATS[l.id]?.streak_days }))
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
    const s = STATS[a.learner_id]
    if (s) {
      s.wcpm_history.push({ date: '2026-10-10', wcpm: next.wcpm })
      s.minutes_read += Math.max(1, Math.round(a.duration_sec / 60))
      s.practicing = next.words.filter((w) => w.label !== 'matched').map((w) => clean(w.text))
      if (s.streak_days === 0) s.streak_days = 1
    }
    return next
  },
  async learnerStats(learnerId) {
    await sleep(200)
    return structuredClone(STATS[learnerId] ?? { stars: 0, streak_days: 0, minutes_read: 0, wcpm_history: [], practicing: [] })
  },
  async practice(learnerId) {
    const latest = [...store.values()].reverse().find((a) => a.learner_id === learnerId)
    const passage = PASSAGES.find((p) => p.id === latest?.passage_id) ?? PASSAGES[0]
    const sentences = passage.text.match(/[^.]+\./g) ?? [passage.text]
    const missed = (latest ?? buildAssessment(learnerId, passage)).words.filter((w) => w.label !== 'matched')
    return missed.map<PracticeItem>((w) => ({
      word: clean(w.text),
      sentence: (sentences.find((s) => s.includes(clean(w.text))) ?? passage.text).trim()
    }))
  },
  async checkWord(_audio, word, learnerId) {
    // Scripted for the mockup: first try misses, second try matches (and earns a star).
    await sleep(900)
    const key = `${learnerId}:${word}`
    const tries = (practiceTries.get(key) ?? 0) + 1
    practiceTries.set(key, tries)
    const match = tries >= 2
    if (match && STATS[learnerId]) STATS[learnerId].stars += 1
    return { result: match ? 'match' : 'no_match' }
  }
}
