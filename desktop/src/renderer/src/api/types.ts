// Mirrors docs/API.md. Change the contract there first, then here.

export type WordLabel = 'matched' | 'misread' | 'skipped'

// CRLA's names, lowest first. Our level is an estimate from reading fluency, not an official CRLA result.
export type Level = 'Low Emerging' | 'High Emerging' | 'Developing' | 'Transitioning' | 'At Grade Level'

export interface Word {
  i: number
  text: string
  label: WordLabel
  score: number
  start: number | null // null when the aligner couldn't time the word (usually a skipped one)
  end: number | null
}

export interface Pause {
  before_word: number
  seconds: number
}

export interface Assessment {
  assessment_id: string
  learner_id: string
  passage_id: string
  duration_sec: number
  words: Word[]
  pauses: Pause[]
  wcpm: number | null // null from /assess for now; saved checks always have a number
  level: Level | null // a saved check always has one, but the database allows NULL
  status: 'draft' | 'confirmed'
  timings?: { convert_ms: number; align_ms: number; score_ms: number }
}

export interface Learner {
  id: string
  display_name: string
  grade: number
  level?: Level
  last_check?: string
  needs_practice?: boolean
  stars?: number
  streak_days?: number
  latest_wcpm?: number
}

// Proposed in docs/API.md: GET /learners/{id}/stats
export interface LearnerStats {
  stars: number
  streak_days: number
  minutes_read: number
  wcpm_history: { date: string; wcpm: number }[]
  practicing: string[]
  days_read: string[]
}

export type Category = 'bukid' | 'pamilya' | 'hayop' | 'kalikasan' | 'paaralan'

export interface Passage {
  id: string
  title: string
  language: string
  grade: number
  text: string
  category: Category
}

export interface RecentCheck {
  assessment_id: string
  learner_id: string
  display_name: string
  date: string
  passage_title: string
  wcpm: number
}

export interface BookWord {
  i: number
  text: string
  start: number
  end: number
}

export interface Book {
  id: string
  title: string
  language: string
  category: Category
  text: string
  reader?: string
  has_recording: boolean
  duration_sec?: number
  words?: BookWord[]
  audio_url?: string
}

export interface NewBook {
  title: string
  language: string
  category: Category
  text: string
  reader: string
}

export interface Storage {
  audio_files: number
  audio_mb: number
  db_mb: number
  data_dir: string
}

export interface ClassSettings {
  teacher_name: string
  section: string
  grade: number
}

export interface Health {
  ok: boolean
  models: { aligner: string; ollama: string }
}

export interface PracticeItem {
  word: string
  sentence: string
  // Where a fluent reading of this word is, for "Hear it": GET /books/{book_id}/clips/{word_index}. Both null when no book has the word.
  book_id: string | null
  word_index: number | null
}

// GET /learners/{id}/progress: the latest two confirmed checks on the same passage. Empty lists and nulls when there's no pair yet.
export interface ProgressCheck {
  assessment_id: string
  passage_id: string
  confirmed_at: string
  wcpm: number | null
  level: Level | null
}

export interface ProgressWord {
  i: number
  text: string
  before: WordLabel | null
  after: WordLabel | null
}

export interface Progress {
  checks: ProgressCheck[] // [before, after]
  words: ProgressWord[]
  wcpm_before: number | null
  wcpm_after: number | null
  wcpm_change: number | null
}

export interface Api {
  mode: 'mock' | 'engine'
  health(): Promise<Health>
  learners(): Promise<Learner[]>
  passages(): Promise<Passage[]>
  assess(audio: Blob, learnerId: string, passageId: string): Promise<Assessment>
  overrideWord(id: string, i: number, label: WordLabel): Promise<Assessment>
  confirm(id: string): Promise<Assessment>
  learnerStats(learnerId: string): Promise<LearnerStats>
  practice(learnerId: string): Promise<PracticeItem[]>
  clipUrl(bookId: string, wordIndex: number): string | null
  progress(learnerId: string): Promise<Progress>
  checkWord(audio: Blob, word: string, learnerId: string): Promise<{ result: 'match' | 'no_match' }>
  recentChecks(): Promise<RecentCheck[]>
  books(): Promise<Book[]>
  book(id: string): Promise<Book>
  createBook(book: NewBook, audio: Blob, durationSec: number): Promise<Book>
  storage(): Promise<Storage>
  deleteAllAudio(): Promise<{ deleted: number }>
  addLearner(name: string): Promise<Learner>
  renameLearner(id: string, name: string): Promise<Learner>
  classSettings(): Promise<ClassSettings>
  saveClassSettings(settings: Partial<ClassSettings>): Promise<ClassSettings>
}
