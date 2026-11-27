import { describe, expect, it } from 'vitest'
import { EXPLAIN_TARGETS } from '../types/proposed'
import { residual } from '../features/explanations/explain'
import { mockExplanation } from './explanations'
import { MOCK_PREDICTIONS } from './predictions'

describe('mock SHAP explanations', () => {
  it('add up: base value + contributions = the prediction, for every architecture and target', () => {
    for (const p of MOCK_PREDICTIONS) {
      for (const target of EXPLAIN_TARGETS) {
        const e = mockExplanation(p.architecture_id, target)!
        expect(e, `${p.architecture_id}/${target}`).toBeDefined()
        expect(residual(e)).toBe(0)
      }
    }
  })
  it('agree with the mock predictions', () => {
    expect(mockExplanation('monolith', 'latency_p95_ms')!.prediction).toBe(160)
    expect(mockExplanation('microservices', 'monthly_cost_usd')!.prediction).toBe(5400)
  })
  it('returns nothing for an unknown architecture', () => {
    expect(mockExplanation('nope', 'latency_p95_ms')).toBeUndefined()
  })
})
