import type { PredictionResult } from '../types'
import type { RankedArchitecture, RecommendationResponse, Weights } from '../types/proposed'
import { BETTER, valuesOf } from '../features/recommendation/criteria'
import { normalizeWeights, topsis } from '../features/recommendation/topsis'

// MOCK backend for POST /recommendations: ranks the candidates with the reference TOPSIS.
export function mockRecommend(weights: Weights, predictions: PredictionResult[]): RecommendationResponse {
  const normalized = normalizeWeights(weights) // throws on unusable weights
  const alternatives = predictions.map((p) => ({ id: p.architecture_id, values: valuesOf(p) }))
  const { scores, excluded } = topsis(alternatives, normalized, BETTER)

  const ranking: RankedArchitecture[] = predictions.map((p, i) => {
    const violations: string[] = []
    if (!p.sla_compliance.meets_latency_sla) violations.push('Misses the latency SLA')
    if (!p.sla_compliance.meets_budget_sla) violations.push('Over budget')
    return {
      architecture_id: p.architecture_id,
      rank: 0,
      closeness: scores[i].closeness,
      values: alternatives[i].values,
      feasible: violations.length === 0,
      violations,
    }
  })
  ranking.sort((a, b) => b.closeness - a.closeness || a.architecture_id.localeCompare(b.architecture_id))
  ranking.forEach((r, i) => (r.rank = i + 1))

  return {
    method: 'topsis',
    weights_used: normalized,
    excluded_criteria: excluded,
    ranking,
    recommended_id: ranking.find((r) => r.feasible)?.architecture_id ?? null,
    data_origin: 'simulated',
  }
}
