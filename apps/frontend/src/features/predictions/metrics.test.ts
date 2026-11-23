import { describe, expect, it } from 'vitest'
import { MOCK_PREDICTIONS } from '../../mocks/handlers'
import { bestValue, buildRadar, fmtSigned, relativeScore } from './metrics'

describe('relativeScore', () => {
  it('gives the best value 100 and others the ratio to it (lower is better)', () => {
    expect(relativeScore(100, 100, 'lower')).toBe(100)
    expect(relativeScore(200, 100, 'lower')).toBe(50)
  })
  it('works for higher-is-better metrics', () => {
    expect(relativeScore(5000, 10000, 'higher')).toBe(50)
    expect(relativeScore(10000, 10000, 'higher')).toBe(100)
  })
  it('handles zero without dividing by zero', () => {
    expect(relativeScore(0, 0, 'lower')).toBe(100)
    expect(relativeScore(5, 0, 'lower')).toBe(0)
    expect(relativeScore(0, 0, 'higher')).toBe(100)
  })
})

describe('bestValue', () => {
  it('picks min or max by direction', () => {
    expect(bestValue([3, 1, 2], 'lower')).toBe(1)
    expect(bestValue([3, 1, 2], 'higher')).toBe(3)
  })
})

describe('fmtSigned', () => {
  it('shows the sign explicitly', () => {
    expect(fmtSigned(35, ' ms')).toBe('+35 ms')
    expect(fmtSigned(-10, ' ms')).toBe('-10 ms')
  })
})

describe('buildRadar', () => {
  it('scores every architecture on six axes with the best at 100', () => {
    const { rows, skipped } = buildRadar(MOCK_PREDICTIONS)
    expect(skipped).toEqual([])
    expect(rows).toHaveLength(6)
    const cost = rows.find((r) => r.axis === 'Cost')!
    expect(cost.monolith).toBe(100) // cheapest
    expect(Number(cost.microservices)).toBeLessThan(50)
    const rps = rows.find((r) => r.axis === 'Throughput')!
    expect(rps.microservices).toBe(100) // highest throughput
  })

  it('leaves out an axis when one architecture lacks the optional field', () => {
    const noScalability = structuredClone(MOCK_PREDICTIONS)
    delete noScalability[1].predictions.scalability
    const { rows, skipped } = buildRadar(noScalability)
    expect(skipped).toEqual(['Scalability headroom'])
    expect(rows.map((r) => r.axis)).not.toContain('Scalability headroom')
  })
})
