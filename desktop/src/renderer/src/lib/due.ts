import type { Learner } from '@/api/types'

/** ISO date (YYYY-MM-DD) one week ago. */
export function weekAgo(): string {
  return new Date(Date.now() - 7 * 86_400_000).toISOString().slice(0, 10)
}

/** A learner is due for a reading check if they haven't been checked in the last 7 days. */
export function isDue(l: Learner, since = weekAgo()): boolean {
  return !l.last_check || l.last_check < since
}

/** Who to check next: never-checked learners first, then the longest since their last check. */
export function nextDue(learners: Learner[]): Learner | undefined {
  const since = weekAgo()
  return [...learners].filter((l) => isDue(l, since)).sort((a, b) => (a.last_check ?? '').localeCompare(b.last_check ?? ''))[0]
}
