import { CRITERIA_KEYS, type CriterionKey, type Weights } from '../../types/proposed'
import type { Better } from '../predictions/metrics'

// REFERENCE implementation of TOPSIS (README section 19). In the real system this runs
// in the backend (ml/src/recommendation/scoring.py); the frontend only calls the API.
// It lives here so the mock API returns correct rankings and the backend owner has a
// worked example with tests to compare against.

export interface Alternative {
  id: string
  values: Record<CriterionKey, number | null>
}

export interface TopsisResult {
  /** Same order as the input alternatives. */
  scores: { id: string; closeness: number }[]
  /** Criteria that had a weight above 0 but were skipped because some alternative has no value. */
  excluded: CriterionKey[]
}

/** Scale weights so they sum to 1. Throws when they are unusable. */
export function normalizeWeights(w: Weights): Weights {
  const values = CRITERIA_KEYS.map((k) => w[k])
  if (values.some((v) => !Number.isFinite(v) || v < 0)) throw new Error('Weights must be numbers of 0 or more')
  const sum = values.reduce((a, b) => a + b, 0)
  if (sum <= 0) throw new Error('At least one weight must be above 0')
  return Object.fromEntries(CRITERIA_KEYS.map((k) => [k, w[k] / sum])) as Weights
}

export function topsis(alternatives: Alternative[], weights: Weights, better: Record<CriterionKey, Better>): TopsisResult {
  const w = normalizeWeights(weights)
  const excluded: CriterionKey[] = []
  const used: CriterionKey[] = []
  for (const k of CRITERIA_KEYS) {
    if (w[k] <= 0) continue
    if (alternatives.some((a) => a.values[k] === null)) excluded.push(k)
    else used.push(k)
  }

  // Step 1: vector-normalize each criterion column, then apply the weight.
  const weighted = alternatives.map(() => ({}) as Record<CriterionKey, number>)
  for (const k of used) {
    const norm = Math.sqrt(alternatives.reduce((s, a) => s + (a.values[k] as number) ** 2, 0))
    alternatives.forEach((a, i) => {
      weighted[i][k] = norm === 0 ? 0 : (w[k] * (a.values[k] as number)) / norm
    })
  }

  // Step 2: the ideal solution takes the best value per criterion, the anti-ideal the worst.
  const ideal = {} as Record<CriterionKey, number>
  const anti = {} as Record<CriterionKey, number>
  for (const k of used) {
    const col = weighted.map((r) => r[k])
    const lo = Math.min(...col)
    const hi = Math.max(...col)
    ideal[k] = better[k] === 'lower' ? lo : hi
    anti[k] = better[k] === 'lower' ? hi : lo
  }

  // Step 3: relative closeness = distance to anti-ideal / (distance to ideal + distance to anti-ideal).
  const scores = alternatives.map((a, i) => {
    let dPlus = 0
    let dMinus = 0
    for (const k of used) {
      dPlus += (weighted[i][k] - ideal[k]) ** 2
      dMinus += (weighted[i][k] - anti[k]) ** 2
    }
    dPlus = Math.sqrt(dPlus)
    dMinus = Math.sqrt(dMinus)
    const total = dPlus + dMinus
    // No separation at all (all identical, or nothing to compare): call it a tie at 0.5.
    return { id: a.id, closeness: total === 0 ? 0.5 : dMinus / total }
  })

  return { scores, excluded }
}
