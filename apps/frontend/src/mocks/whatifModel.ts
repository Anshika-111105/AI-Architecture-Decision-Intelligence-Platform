import type { PredictionResult } from '../types'
import type { Scenario } from '../types/proposed'

// MOCK performance model for POST /what-if. The formulas are INVENTED so the sliders
// behave sensibly (more load = slower, more replicas = faster and dearer). They are NOT
// the trained model and say nothing about real systems.

const CAPACITY_PER_VCPU = 1600 // requests per second one vCPU can serve
const DB_MS: Record<Scenario['database'], number> = { postgres: 30, mysql: 32, mongodb: 28, dynamodb: 22, cassandra: 25, redis_only: 12, none: 5 }
const DB_COST: Record<Scenario['database'], number> = { postgres: 150, mysql: 130, mongodb: 170, dynamodb: 120, cassandra: 220, redis_only: 100, none: 0 }
const CACHE_HIT: Record<Scenario['cache'], number> = { none: 0, redis: 0.6, memcached: 0.5, hazelcast: 0.55 }
const CACHE_COST: Record<Scenario['cache'], number> = { none: 0, redis: 90, memcached: 70, hazelcast: 110 }
const BROKER_COST: Record<Scenario['messaging'], number> = { none: 0, kafka: 200, rabbitmq: 120, aws_sqs: 40, nats: 60 }
const CLOUD_FACTOR: Record<Scenario['cloud'], number> = { aws: 1, gcp: 0.95, azure: 1.03, on_premise: 0.8 }

const round = (v: number, digits = 1) => Math.round(v * 10 ** digits) / 10 ** digits

export function mockWhatIfPredictions(s: Scenario): PredictionResult['predictions'] {
  const cacheShare = s.read_write_ratio * CACHE_HIT[s.cache] // share of requests answered from cache
  const workPerRequest = 1 - 0.5 * cacheShare
  const capacity = s.replica_count * s.cpu_limit * CAPACITY_PER_VCPU
  const util = (s.rps * workPerRequest) / capacity

  const serviceMs = 18 + DB_MS[s.database] * (1 - 0.7 * cacheShare)
  const concurrencyPenalty = 1 + 0.1 * Math.min(1, s.concurrency / (s.replica_count * s.cpu_limit * 1000))
  const p50 = (serviceMs * concurrencyPenalty) / (1 - Math.min(util, 0.97)) // queueing: latency explodes near saturation

  const memoryShare = Math.min(0.98, 0.25 + 0.5 * Math.min(util, 1) + Math.min(0.2, s.data_size / 10000))
  const cost = (s.replica_count * (s.cpu_limit * 30 + s.memory_limit * 4) + DB_COST[s.database] + s.data_size * 0.1 + CACHE_COST[s.cache] + BROKER_COST[s.messaging]) * CLOUD_FACTOR[s.cloud]

  return {
    latency: { p50_ms: round(p50), p90_ms: round(p50 * 1.9), p95_ms: round(p50 * 2.4), p99_ms: round(p50 * 3.6) },
    throughput: { predicted_rps: round(Math.min(s.rps, capacity / workPerRequest), 0) },
    resources: { cpu_utilization_pct: round(Math.min(100, util * 100)), memory_utilization_mb: round(s.replica_count * s.memory_limit * 1024 * memoryShare, 0) },
    cost: { estimated_monthly_usd: round(cost, 0) },
  }
}
