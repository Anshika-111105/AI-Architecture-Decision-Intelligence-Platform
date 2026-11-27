import type { Better } from '../predictions/metrics'

export interface Delta {
  abs: number
  /** Percent change versus the current value; null when the current value is 0. */
  pct: number | null
  verdict: 'better' | 'worse' | 'same'
}

export function deltaOf(current: number, whatIf: number, better: Better): Delta {
  const abs = whatIf - current
  if (Math.abs(abs) < 1e-9) return { abs: 0, pct: 0, verdict: 'same' }
  const improved = better === 'lower' ? abs < 0 : abs > 0
  return { abs, pct: current === 0 ? null : (abs / Math.abs(current)) * 100, verdict: improved ? 'better' : 'worse' }
}
