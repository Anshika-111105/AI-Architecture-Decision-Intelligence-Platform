import type { PredictionResult } from '../types'

// MOCK DATA: shaped like packages/shared-schemas/prediction.schema.json.
// These numbers are invented for UI development only. They are NOT predictions
// from the trained model and must never be shown as real results.
//
// The three profiles are deliberately different so the charts show real trade-offs:
// the monolith is cheap but slower, microservices are fast and scalable but cost more.
const MOCK_LATENCY_SLA_MS = 150
const MOCK_BUDGET_USD = 5000

interface MockProfile {
  id: string
  p50: number
  p90: number
  p95: number
  p99: number
  rps: number
  cpu: number
  mem: number
  cost: number
  err: number
  avail: number
  maxRps: number
  headroom: number
}

const PROFILES: MockProfile[] = [
  { id: 'monolith', p50: 55, p90: 120, p95: 160, p99: 260, rps: 3200, cpu: 62, mem: 1800, cost: 1800, err: 0.3, avail: 99.9, maxRps: 5000, headroom: 1.4 },
  { id: 'modular_monolith', p50: 45, p90: 100, p95: 135, p99: 220, rps: 4300, cpu: 55, mem: 2300, cost: 2600, err: 0.22, avail: 99.93, maxRps: 7500, headroom: 1.8 },
  { id: 'microservices', p50: 38, p90: 85, p95: 115, p99: 190, rps: 6200, cpu: 48, mem: 4100, cost: 5400, err: 0.15, avail: 99.97, maxRps: 14000, headroom: 2.8 },
]

// SLA flags and margins are COMPUTED from the numbers above, so they can never contradict each other.
const toPrediction = (m: MockProfile): PredictionResult => ({
  architecture_id: m.id,
  predictions: {
    latency: { p50_ms: m.p50, p90_ms: m.p90, p95_ms: m.p95, p99_ms: m.p99 },
    throughput: { predicted_rps: m.rps },
    resources: { cpu_utilization_pct: m.cpu, memory_utilization_mb: m.mem },
    cost: { estimated_monthly_usd: m.cost },
    reliability: { estimated_error_rate_pct: m.err, availability_score: m.avail },
    scalability: { max_supported_rps: m.maxRps, scalability_headroom_multiplier: m.headroom },
  },
  sla_compliance: {
    meets_latency_sla: m.p95 <= MOCK_LATENCY_SLA_MS,
    meets_budget_sla: m.cost <= MOCK_BUDGET_USD,
    latency_margin_ms: MOCK_LATENCY_SLA_MS - m.p95,
    budget_margin_usd: MOCK_BUDGET_USD - m.cost,
  },
  explainability: {
    top_contributing_features: [
      { feature: 'rps', shap_value: 0.42, impact: 'increases_latency' },
      { feature: 'cache=redis', shap_value: -0.3, impact: 'decreases_latency' },
      { feature: 'replica_count', shap_value: -0.18, impact: 'decreases_latency' },
    ],
    summary: 'Mock explanation for UI development.',
  },
})

export const MOCK_PREDICTIONS: PredictionResult[] = PROFILES.map(toPrediction)
