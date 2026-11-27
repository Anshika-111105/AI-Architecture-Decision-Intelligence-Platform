import type { PredictionResult } from '../../types'
import { CRITERIA_KEYS, type CriterionKey, type Weights } from '../../types/proposed'
import { METRICS, type Better, type MetricDef } from '../predictions/metrics'

// The four TOPSIS criteria from README section 19, each tied to one prediction metric.
// ASSUMPTION to confirm with the backend owner: latency uses p95, scalability uses the
// headroom multiplier, and reliability uses the error rate (lower is better). Error
// rate is used instead of the availability score because availability is nearly
// identical across architectures (99.9 vs 99.97), so it would barely move the ranking.
const SOURCE: Record<CriterionKey, { metricKey: string; label: string; note: string }> = {
  latency: { metricKey: 'p95', label: 'Latency', note: 'p95 response time, lower is better' },
  cost: { metricKey: 'cost', label: 'Cost', note: 'estimated monthly cost, lower is better' },
  scalability: { metricKey: 'headroom', label: 'Scalability', note: 'headroom multiplier, higher is better' },
  reliability: { metricKey: 'err', label: 'Reliability', note: 'estimated error rate, lower is better' },
}

export interface Criterion {
  key: CriterionKey
  label: string
  note: string
  better: Better
  metric: MetricDef
}

export const CRITERIA: Criterion[] = CRITERIA_KEYS.map((key) => {
  const s = SOURCE[key]
  const metric = METRICS.find((m) => m.key === s.metricKey)
  if (!metric) throw new Error(`No metric "${s.metricKey}" for criterion "${key}"`)
  return { key, label: s.label, note: s.note, better: metric.better, metric }
})

export const criterionOf = (key: CriterionKey): Criterion => CRITERIA.find((c) => c.key === key)!

export const BETTER = Object.fromEntries(CRITERIA.map((c) => [c.key, c.better])) as Record<CriterionKey, Better>

/** README section 19 example: latency 35%, cost 25%, scalability 20%, reliability 20%. */
export const DEFAULT_WEIGHTS: Weights = { latency: 35, cost: 25, scalability: 20, reliability: 20 }

export function valuesOf(p: PredictionResult): Record<CriterionKey, number | null> {
  return Object.fromEntries(CRITERIA.map((c) => [c.key, c.metric.value(p) ?? null])) as Record<CriterionKey, number | null>
}
