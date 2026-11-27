import { describe, expect, it } from 'vitest'
import type { CriterionKey } from '../../types/proposed'
import { BETTER } from './criteria'
import { normalizeWeights, topsis, type Alternative } from './topsis'

const none = { latency: null, cost: null, scalability: null, reliability: null }
const alt = (id: string, v: Partial<Record<CriterionKey, number>>): Alternative => ({ id, values: { ...none, ...v } })
const W = (w: Partial<Record<CriterionKey, number>>) => ({ latency: 0, cost: 0, scalability: 0, reliability: 0, ...w })
const score = (r: ReturnType<typeof topsis>, id: string) => r.scores.find((s) => s.id === id)!.closeness

describe('normalizeWeights', () => {
  it('scales weights to sum to 1', () => {
    const n = normalizeWeights({ latency: 35, cost: 25, scalability: 20, reliability: 20 })
    expect(n.latency).toBeCloseTo(0.35)
    expect(Object.values(n).reduce((a, b) => a + b, 0)).toBeCloseTo(1)
  })
  it('rejects all-zero and negative weights', () => {
    expect(() => normalizeWeights(W({}))).toThrow(/above 0/)
    expect(() => normalizeWeights(W({ cost: -1, latency: 5 }))).toThrow(/0 or more/)
  })
})

describe('topsis', () => {
  it('gives 1 to an option that is best on every criterion and 0 to the worst', () => {
    // latency: lower is better, scalability: higher is better
    const r = topsis(
      [alt('X', { latency: 100, scalability: 30 }), alt('Y', { latency: 200, scalability: 10 })],
      W({ latency: 1, scalability: 1 }),
      BETTER,
    )
    expect(score(r, 'X')).toBeCloseTo(1)
    expect(score(r, 'Y')).toBeCloseTo(0)
  })

  it('ties a perfectly symmetric trade-off at 0.5', () => {
    const r = topsis(
      [alt('A', { latency: 100, scalability: 10 }), alt('B', { latency: 200, scalability: 20 })],
      W({ latency: 1, scalability: 1 }),
      BETTER,
    )
    expect(score(r, 'A')).toBeCloseTo(0.5)
    expect(score(r, 'B')).toBeCloseTo(0.5)
  })

  it('follows the weights: the same options rank differently when priorities change', () => {
    const options = [alt('fast', { latency: 100, scalability: 10 }), alt('scalable', { latency: 200, scalability: 20 })]
    const latencyFirst = topsis(options, W({ latency: 9, scalability: 1 }), BETTER)
    const scaleFirst = topsis(options, W({ latency: 1, scalability: 9 }), BETTER)
    expect(score(latencyFirst, 'fast')).toBeGreaterThan(score(latencyFirst, 'scalable'))
    expect(score(scaleFirst, 'scalable')).toBeGreaterThan(score(scaleFirst, 'fast'))
  })

  it('ignores a criterion with weight 0, even when its values are missing', () => {
    const r = topsis(
      [alt('A', { latency: 100 }), alt('B', { latency: 200 })],
      W({ latency: 1 }),
      BETTER,
    )
    expect(r.excluded).toEqual([])
    expect(score(r, 'A')).toBeGreaterThan(score(r, 'B'))
  })

  it('excludes a weighted criterion when an option has no value for it, and says so', () => {
    const r = topsis(
      [alt('A', { latency: 100, cost: 5 }), alt('B', { latency: 200 })],
      W({ latency: 1, cost: 1 }),
      BETTER,
    )
    expect(r.excluded).toEqual(['cost'])
    expect(score(r, 'A')).toBeGreaterThan(score(r, 'B')) // decided on latency alone
  })

  it('returns 0.5 for everyone when nothing separates the options', () => {
    const r = topsis([alt('A', { latency: 100 }), alt('B', { latency: 100 })], W({ latency: 1 }), BETTER)
    expect(score(r, 'A')).toBe(0.5)
    expect(score(r, 'B')).toBe(0.5)
  })
})
