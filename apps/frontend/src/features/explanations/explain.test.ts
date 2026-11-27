import { describe, expect, it } from 'vitest'
import type { ExplanationResponse } from '../../types/proposed'
import { chartRows, describe as describeContribution, residual } from './explain'

const base: ExplanationResponse = {
  architecture_id: 'monolith',
  target: 'latency_p95_ms',
  base_value: 140,
  prediction: 160,
  contributions: [
    { feature: 'rps', feature_value: 5000, shap_value: 28 },
    { feature: 'cache', feature_value: 'redis', shap_value: -12 },
    { feature: 'replica_count', feature_value: 3, shap_value: 4 },
  ],
  data_origin: 'simulated',
}

describe('residual', () => {
  it('is 0 when the contributions add up to prediction minus base', () => {
    expect(residual(base)).toBe(0)
  })
  it('captures what unlisted features must add up to', () => {
    const truncated = { ...base, contributions: base.contributions.slice(0, 2) } // drops +4
    expect(residual(truncated)).toBe(4)
  })
})

describe('chartRows', () => {
  it('sorts by absolute effect and splits raises from lowers', () => {
    const rows = chartRows(base)
    expect(rows.map((r) => r.label)).toEqual(['rps = 5,000', 'cache = redis', 'replica_count = 3'])
    expect(rows[0]).toMatchObject({ raises: 28, lowers: 0 })
    expect(rows[1]).toMatchObject({ raises: 0, lowers: -12 })
  })
  it('bundles weaker features and any unlisted remainder into "All other features"', () => {
    const rows = chartRows(base, 1)
    expect(rows).toHaveLength(2)
    expect(rows[1]).toMatchObject({ label: 'All other features', raises: 0, lowers: -8 }) // -12 + 4
  })
  it('adds the remainder row when features are missing from the response', () => {
    const rows = chartRows({ ...base, contributions: base.contributions.slice(0, 2) })
    expect(rows.at(-1)).toMatchObject({ label: 'All other features', raises: 4 })
  })
})

describe('describe', () => {
  it('writes a plain-language sentence with the unit', () => {
    expect(describeContribution(base.contributions[0], 'latency_p95_ms')).toBe('rps = 5,000 raises the predicted p95 latency by 28 ms')
    expect(describeContribution(base.contributions[1], 'latency_p95_ms')).toBe('cache = redis lowers the predicted p95 latency by 12 ms')
  })
})
