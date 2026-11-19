import { http, HttpResponse } from 'msw'
import type { PredictionResult } from '../types'

// MOCK DATA: shaped like packages/shared-schemas/prediction.schema.json.
// These numbers are invented for UI development only. They are NOT predictions
// from the trained model and must never be shown as real results.
const mockPrediction = (architecture_id: string, scale: number): PredictionResult => ({
  architecture_id,
  predictions: {
    latency: { p50_ms: 40 * scale, p90_ms: 90 * scale, p95_ms: 120 * scale, p99_ms: 210 * scale },
    throughput: { predicted_rps: 4200 / scale },
    resources: { cpu_utilization_pct: Math.min(95, 45 * scale), memory_utilization_mb: 2048 * scale },
    cost: { estimated_monthly_usd: 3200 * scale },
    reliability: { estimated_error_rate_pct: 0.2 * scale, availability_score: 99.95 },
    scalability: { max_supported_rps: 9000 / scale, scalability_headroom_multiplier: 2 / scale },
  },
  sla_compliance: {
    meets_latency_sla: scale <= 1.5,
    meets_budget_sla: scale <= 1.2,
    latency_margin_ms: 200 - 210 * scale,
    budget_margin_usd: 5000 - 3200 * scale,
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

export const handlers = [
  http.get('/api/v1/predictions', () =>
    HttpResponse.json([
      mockPrediction('monolith', 1),
      mockPrediction('modular_monolith', 1.1),
      mockPrediction('microservices', 1.4),
    ]),
  ),
]
