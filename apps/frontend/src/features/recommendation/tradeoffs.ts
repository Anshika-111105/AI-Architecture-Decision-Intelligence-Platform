import type { RankedArchitecture } from '../../types/proposed'
import { CRITERIA } from './criteria'

export interface TradeOff {
  label: string
  pick: string
  other: string
  verdict: 'better' | 'worse' | 'same' | 'unknown'
}

/** Criterion-by-criterion comparison of the recommended option against another one. */
export function compareOptions(pick: RankedArchitecture, other: RankedArchitecture): TradeOff[] {
  return CRITERIA.map((c) => {
    const a = pick.values[c.key]
    const b = other.values[c.key]
    if (a === null || b === null) {
      return { label: c.label, pick: a === null ? 'n/a' : c.metric.format(a), other: b === null ? 'n/a' : c.metric.format(b), verdict: 'unknown' }
    }
    const verdict = a === b ? 'same' : (c.better === 'lower') === a < b ? 'better' : 'worse'
    return { label: c.label, pick: c.metric.format(a), other: c.metric.format(b), verdict }
  })
}
