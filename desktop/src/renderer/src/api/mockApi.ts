import type { Api, Assessment, Book, BookWord, Learner, LearnerStats, Passage, PracticeItem, RecentCheck, Word, WordLabel } from './types'

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

// Sample check dates are relative to today so "this week" stays meaningful in demos.
function daysAgo(n: number): string {
  return new Date(Date.now() - n * 86_400_000).toISOString().slice(0, 10)
}

const LEARNERS: Learner[] = [
  { id: 'l_01', display_name: 'Lina', grade: 2, level: 'Developing', last_check: daysAgo(1), needs_practice: true },
  { id: 'l_02', display_name: 'Paolo', grade: 2, level: 'Transitioning', last_check: daysAgo(1) },
  { id: 'l_03', display_name: 'Mika', grade: 2, level: 'Grade level', last_check: daysAgo(2) },
  { id: 'l_04', display_name: 'Josie', grade: 2, level: 'Emerging', last_check: daysAgo(4), needs_practice: true },
  { id: 'l_05', display_name: 'Ramon', grade: 2, level: 'Developing', last_check: daysAgo(9), needs_practice: true },
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

const missedThisSession = new Set<string>()

// Evenly spaced word timings: stands in for the aligner until the engine exists.
function evenTimings(text: string, durationSec: number): BookWord[] {
  const words = text.split(/\s+/)
  const step = durationSec / words.length
  return words.map((w, i) => ({ i, text: w, start: +(i * step).toFixed(2), end: +((i + 0.9) * step).toFixed(2) }))
}

function sampleBook(id: string, passageId: string, reader?: string): Book {
  const p = PASSAGES.find((x) => x.id === passageId)!
  const duration = p.text.split(/\s+/).length * 0.55
  return {
    id,
    title: p.title,
    language: p.language,
    category: p.category,
    text: p.text,
    reader,
    has_recording: Boolean(reader),
    duration_sec: reader ? duration : undefined,
    words: reader ? evenTimings(p.text, duration) : undefined
  }
}

const BOOKS: Book[] = [
  sampleBook('b_01', 'fil_g2_01', 'Lola Ising'),
  sampleBook('b_02', 'fil_g2_02', "Ma'am Rose"),
  sampleBook('b_03', 'eng_g2_01', 'Teacher Mark'),
  sampleBook('b_04', 'fil_g2_03')
]

const RECENT: RecentCheck[] = [
  { assessment_id: 'r_1', learner_id: 'l_01', display_name: 'Lina', date: daysAgo(1), passage_title: 'Ang Palay ni Lina', wcpm: 58 },
  { assessment_id: 'r_2', learner_id: 'l_02', display_name: 'Paolo', date: daysAgo(1), passage_title: 'Tuwing Linggo', wcpm: 66 },
  { assessment_id: 'r_3', learner_id: 'l_03', display_name: 'Mika', date: daysAgo(2), passage_title: 'Ang Tamaraw', wcpm: 82 },
  { assessment_id: 'r_4', learner_id: 'l_04', display_name: 'Josie', date: daysAgo(4), passage_title: 'Bagong Libro', wcpm: 27 },
  { assessment_id: 'r_5', learner_id: 'l_05', display_name: 'Ramon', date: daysAgo(9), passage_title: "Ben's Red Kite", wcpm: 49 }
]
let audioFiles = 7

export const mockApi: Api = {
  mode: 'mock',
  async health() {
    await sleep(150)
    return { ok: true, models: { aligner: 'loaded', ollama: 'up' } }
  },
  async learners() {
    await sleep(250)
    return LEARNERS.map((l) => ({
      ...l,
      stars: STATS[l.id]?.stars,
      streak_days: STATS[l.id]?.streak_days,
      latest_wcpm: STATS[l.id]?.wcpm_history.at(-1)?.wcpm
    }))
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
    RECENT.unshift({
      assessment_id: id,
      learner_id: a.learner_id,
      display_name: LEARNERS.find((l) => l.id === a.learner_id)?.display_name ?? '',
      date: daysAgo(0),
      passage_title: PASSAGES.find((p) => p.id === a.passage_id)?.title ?? '',
      wcpm: next.wcpm
    })
    const learner = LEARNERS.find((l) => l.id === a.learner_id)
    if (learner) learner.last_check = daysAgo(0)
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
    missedThisSession.delete(learnerId)
    const latest = [...store.values()].reverse().find((a) => a.learner_id === learnerId)
    const sentences = PASSAGES.flatMap((p) => p.text.match(/[^.]+\./g) ?? [p.text]).map((s) => s.trim())
    const sentenceFor = (word: string) => sentences.find((s) => s.split(/\s+/).some((w) => clean(w) === word)) ?? word
    // Latest check's missed words; otherwise the words the learner is already practicing.
    const words = latest
      ? latest.words.filter((w) => w.label !== 'matched').map((w) => clean(w.text))
      : STATS[learnerId]?.practicing.length
        ? STATS[learnerId].practicing
        : buildAssessment(learnerId, PASSAGES[0]).words.filter((w) => w.label !== 'matched').map((w) => clean(w.text))
    return words.map<PracticeItem>((word) => ({ word, sentence: sentenceFor(word) }))
  },
  async checkWord(_audio, _word, learnerId) {
    // Scripted for the mockup: the first try of a session misses, everything after matches
    // (so a demo shows both "try again" and a combo streak). Each match earns a star.
    await sleep(900)
    const match = missedThisSession.has(learnerId)
    missedThisSession.add(learnerId)
    if (match && STATS[learnerId]) STATS[learnerId].stars += 1
    return { result: match ? 'match' : 'no_match' }
  },
  async recentChecks() {
    await sleep(200)
    return [...RECENT].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 6)
  },
  async books() {
    await sleep(200)
    return [...BOOKS]
  },
  async book(id) {
    await sleep(120)
    const b = BOOKS.find((x) => x.id === id)
    if (!b) throw new Error('Book not found')
    return b
  },
  async createBook(nb, audio, durationSec) {
    await sleep(1800)
    const id = `b_${String(BOOKS.length + 1).padStart(2, '0')}`
    const duration = Math.max(durationSec, 1)
    const book: Book = { id, ...nb, has_recording: true, duration_sec: duration, words: evenTimings(nb.text, duration), audio_url: URL.createObjectURL(audio) }
    BOOKS.unshift(book)
    PASSAGES.push({ id: `book_${id}`, title: nb.title, language: nb.language, grade: 2, category: nb.category, text: nb.text })
    audioFiles += 1
    return book
  },
  async storage() {
    await sleep(150)
    return { audio_files: audioFiles, audio_mb: +(audioFiles * 0.42).toFixed(1), db_mb: 0.3, data_dir: window.basa?.platform === 'win32' ? '%APPDATA%\\Basa' : '~/.config/Basa' }
  },
  async deleteAllAudio() {
    await sleep(400)
    // Model readings in books are kept: only children's recordings are deleted.
    const deleted = Math.max(0, audioFiles - BOOKS.filter((b) => b.has_recording).length)
    audioFiles -= deleted
    return { deleted }
  },
  async addLearner(name) {
    await sleep(200)
    const id = `l_${String(LEARNERS.length + 1).padStart(2, '0')}`
    const l: Learner = { id, display_name: name, grade: 2 }
    LEARNERS.push(l)
    STATS[id] = { stars: 0, streak_days: 0, minutes_read: 0, wcpm_history: [], practicing: [] }
    return l
  },
  async renameLearner(id, name) {
    await sleep(200)
    const l = LEARNERS.find((x) => x.id === id)
    if (!l) throw new Error('Learner not found')
    l.display_name = name
    return l
  }
}
