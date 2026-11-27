import { describe, expect, it } from 'vitest'
import type { RankedArchitecture } from '../../types/proposed'
import { compareOptions } from './tradeoffs'

const opt = (id: string, values: RankedArchitecture['values']): RankedArchitecture => ({
  architecture_id: id,
  rank: 1,
  closeness: 0.5,
  values,
  feasible: true,
  violations: [],
})

describe('compareOptions', () => {
  it('says better or worse per criterion using each criterion\'s direction', () => {
    const t = compareOptions(
      opt('a', { latency: 135, cost: 2600, scalability: 1.8, reliability: 0.22 }),
      opt('b', { latency: 160, cost: 1800, scalability: 1.4, reliability: 0.22 }),
    )
    const verdict = Object.fromEntries(t.map((x) => [x.label, x.verdict]))
    expect(verdict).toEqual({ Latency: 'better', Cost: 'worse', Scalability: 'better', Reliability: 'same' })
    expect(t.find((x) => x.label === 'Cost')).toMatchObject({ pick: '$2,600', other: '$1,800' })
  })

  it('marks a criterion unknown when a value is missing', () => {
    const t = compareOptions(
      opt('a', { latency: 135, cost: 2600, scalability: null, reliability: 0.22 }),
      opt('b', { latency: 160, cost: 1800, scalability: 1.4, reliability: 0.22 }),
    )
    expect(t.find((x) => x.label === 'Scalability')).toMatchObject({ pick: 'n/a', verdict: 'unknown' })
  })
})
