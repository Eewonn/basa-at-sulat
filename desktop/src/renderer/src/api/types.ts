// Mirrors docs/API.md. Change the contract there first, then here.

export type WordLabel = 'matched' | 'misread' | 'skipped'

export interface Word {
  i: number
  text: string
  label: WordLabel
  score: number
  start: number
  end: number
  heard?: string
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
  wcpm: number
  level: string
  status: 'draft' | 'confirmed'
  timings?: { convert_ms: number; align_ms: number; score_ms: number }
}

export interface Learner {
  id: string
  display_name: string
  grade: number
  level?: string
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

export interface Health {
  ok: boolean
  models: { aligner: string; ollama: string }
}

export interface PracticeItem {
  word: string
  sentence: string
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
  checkWord(audio: Blob, word: string, learnerId: string): Promise<{ result: 'match' | 'no_match' }>
}
