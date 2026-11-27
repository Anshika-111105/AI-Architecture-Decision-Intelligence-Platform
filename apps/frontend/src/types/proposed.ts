import type { DataOrigin, PredictionResult } from './index'

// PROPOSED API contracts for /recommendations, /explanations and /what-if.
// The shared JSON schemas (packages/shared-schemas) do not define these yet, and the
// backend routes are still empty. These shapes were designed from README sections
// 19, 20 and 23 so the screens can be built now. Agree them with the backend owner,
// then move them into packages/shared-schemas and generate the types from there.
// See apps/frontend/API_CONTRACT.md.

// ---------- Recommendation (README section 19) ----------
export const CRITERIA_KEYS = ['latency', 'cost', 'scalability', 'reliability'] as const
export type CriterionKey = (typeof CRITERIA_KEYS)[number]
/** Importance of each criterion. Any positive scale; the backend normalizes them to sum to 1. */
export type Weights = Record<CriterionKey, number>

export interface RankedArchitecture {
  architecture_id: string
  /** 1 = best. */
  rank: number
  /** TOPSIS relative closeness to the ideal solution, 0 to 1. */
  closeness: number
  /** The raw numbers the ranking was computed from (null = not available). */
  values: Record<CriterionKey, number | null>
  /** Whether the option meets the latency SLA and the budget. */
  feasible: boolean
  violations: string[]
}

export interface RecommendationResponse {
  method: 'topsis'
  weights_used: Weights
  /** Criteria with a weight above 0 that were left out because some architecture has no value for them. */
  excluded_criteria: CriterionKey[]
  ranking: RankedArchitecture[]
  /** Best-ranked option that satisfies the constraints, or null when none does. */
  recommended_id: string | null
  data_origin: DataOrigin
}

// ---------- SHAP explanation (README section 20) ----------
export const EXPLAIN_TARGETS = ['latency_p95_ms', 'monthly_cost_usd'] as const
export type ExplainTarget = (typeof EXPLAIN_TARGETS)[number]

export interface FeatureContribution {
  feature: string
  feature_value: string | number | boolean | null
  /** In the unit of the target. Positive raises the prediction, negative lowers it. */
  shap_value: number
}

export interface ExplanationResponse {
  architecture_id: string
  target: ExplainTarget
  /** The model's average prediction; base_value + all shap values = prediction. */
  base_value: number
  prediction: number
  contributions: FeatureContribution[]
  data_origin: DataOrigin
  model_version?: string
}

// ---------- What-if (README section 23) ----------
export const DATABASES = ['postgres', 'mysql', 'mongodb', 'dynamodb', 'cassandra', 'redis_only', 'none'] as const
export const CACHES = ['none', 'redis', 'memcached', 'hazelcast'] as const
export const BROKERS = ['none', 'kafka', 'rabbitmq', 'aws_sqs', 'nats'] as const
export const CLOUDS = ['aws', 'gcp', 'azure', 'on_premise'] as const

export interface Scenario {
  rps: number
  concurrency: number
  /** GB. */
  data_size: number
  /** Share of reads, 0 to 1. */
  read_write_ratio: number
  replica_count: number
  /** vCPU per replica. */
  cpu_limit: number
  /** GB per replica. */
  memory_limit: number
  database: (typeof DATABASES)[number]
  cache: (typeof CACHES)[number]
  messaging: (typeof BROKERS)[number]
  cloud: (typeof CLOUDS)[number]
}

export interface WhatIfResponse {
  scenario: Scenario
  predictions: PredictionResult['predictions']
  data_origin: DataOrigin
}
