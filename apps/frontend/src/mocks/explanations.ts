import type { ExplainTarget, ExplanationResponse, FeatureContribution } from '../types/proposed'
import { MOCK_PREDICTIONS } from './predictions'

// MOCK SHAP values: invented for UI development, NOT produced by a trained model
// (README section 20: real direction and size must come from the trained model).
// They do respect the one real property of SHAP: base value + contributions = prediction.
// The last row of each table is computed to make that sum exact.

type Row = [feature: string, value: FeatureContribution['feature_value'], shap: number | 'balance']

const BASE: Record<ExplainTarget, number> = { latency_p95_ms: 140, monthly_cost_usd: 3300 }

const ROWS: Record<ExplainTarget, Record<string, Row[]>> = {
  latency_p95_ms: {
    monolith: [['rps', 5000, 28], ['concurrency', 5000, 12], ['cache', 'redis', -12], ['replica_count', 3, -5], ['service_count', 1, 2], ['network_hops', 1, 'balance']],
    modular_monolith: [['rps', 5000, 14], ['concurrency', 5000, 6], ['cache', 'redis', -14], ['replica_count', 4, -10], ['service_count', 4, 1], ['network_hops', 2, 'balance']],
    microservices: [['rps', 5000, 8], ['concurrency', 5000, 4], ['cache', 'redis', -22], ['replica_count', 6, -24], ['service_count', 12, 2], ['network_hops', 6, 'balance']],
  },
  monthly_cost_usd: {
    monolith: [['replica_count', 3, 120], ['cpu_limit', 2, 100], ['memory_limit', 4, 60], ['cache', 'redis', 60], ['messaging', 'none', -400], ['service_count', 1, 'balance']],
    modular_monolith: [['replica_count', 4, 160], ['cpu_limit', 2, 100], ['memory_limit', 4, 60], ['cache', 'redis', 60], ['messaging', 'rabbitmq', 120], ['service_count', 4, 'balance']],
    microservices: [['replica_count', 6, 300], ['cpu_limit', 2, 100], ['memory_limit', 4, 60], ['cache', 'redis', 60], ['messaging', 'kafka', 400], ['service_count', 12, 'balance']],
  },
}

const predictionFor = (arch: string, target: ExplainTarget): number | undefined => {
  const p = MOCK_PREDICTIONS.find((x) => x.architecture_id === arch)
  if (!p) return undefined
  return target === 'latency_p95_ms' ? p.predictions.latency.p95_ms : p.predictions.cost.estimated_monthly_usd
}

export function mockExplanation(arch: string, target: ExplainTarget): ExplanationResponse | undefined {
  const prediction = predictionFor(arch, target)
  const rows = ROWS[target]?.[arch]
  if (prediction === undefined || !rows) return undefined
  const base = BASE[target]
  const fixed = rows.reduce((s, r) => s + (r[2] === 'balance' ? 0 : r[2]), 0)
  const contributions: FeatureContribution[] = rows.map(([feature, feature_value, shap]) => ({
    feature,
    feature_value,
    shap_value: shap === 'balance' ? prediction - base - fixed : shap,
  }))
  return { architecture_id: arch, target, base_value: base, prediction, contributions, data_origin: 'simulated', model_version: 'mock' }
}
