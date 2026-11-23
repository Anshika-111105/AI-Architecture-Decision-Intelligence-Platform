import type { PredictionResult } from '../../types'

// One definition per metric the prediction schema can contain. Both the dashboard
// and the comparison page read from this list, so labels, units and "which
// direction is better" are defined exactly once.
export type Better = 'lower' | 'higher'
export type Group = 'Latency' | 'Throughput' | 'Cost' | 'Resources' | 'Reliability' | 'Scalability'

export interface MetricDef {
  key: string
  label: string
  group: Group
  better: Better
  value: (p: PredictionResult) => number | undefined
  format: (v: number) => string
  /** Present only for the metrics drawn on the radar chart. */
  radarLabel?: string
}

// Fixed locale so numbers look the same on every machine (and in tests).
const num = (v: number, digits = 0) => v.toLocaleString('en-US', { maximumFractionDigits: digits })
export const fmtMs = (v: number) => `${num(v, 1)} ms`
export const fmtRps = (v: number) => `${num(v)} req/s`
export const fmtUsd = (v: number) => `$${num(v)}`
export const fmtPct = (v: number, digits = 2) => `${num(v, digits)}%`
export const fmtSigned = (v: number, suffix: string) => `${v >= 0 ? '+' : '-'}${num(Math.abs(v), 1)}${suffix}`

export const GROUPS: Group[] = ['Latency', 'Throughput', 'Cost', 'Resources', 'Reliability', 'Scalability']

export const METRICS: MetricDef[] = [
  { key: 'p50', label: 'Latency p50', group: 'Latency', better: 'lower', value: (p) => p.predictions.latency.p50_ms, format: fmtMs },
  { key: 'p90', label: 'Latency p90', group: 'Latency', better: 'lower', value: (p) => p.predictions.latency.p90_ms, format: fmtMs },
  { key: 'p95', label: 'Latency p95', group: 'Latency', better: 'lower', value: (p) => p.predictions.latency.p95_ms, format: fmtMs, radarLabel: 'Latency (p95)' },
  { key: 'p99', label: 'Latency p99', group: 'Latency', better: 'lower', value: (p) => p.predictions.latency.p99_ms, format: fmtMs },
  { key: 'rps', label: 'Predicted throughput', group: 'Throughput', better: 'higher', value: (p) => p.predictions.throughput.predicted_rps, format: fmtRps, radarLabel: 'Throughput' },
  { key: 'cost', label: 'Estimated monthly cost', group: 'Cost', better: 'lower', value: (p) => p.predictions.cost.estimated_monthly_usd, format: fmtUsd, radarLabel: 'Cost' },
  { key: 'cpu', label: 'CPU utilization', group: 'Resources', better: 'lower', value: (p) => p.predictions.resources.cpu_utilization_pct, format: (v) => fmtPct(v, 1), radarLabel: 'CPU use' },
  { key: 'mem', label: 'Memory utilization', group: 'Resources', better: 'lower', value: (p) => p.predictions.resources.memory_utilization_mb, format: (v) => `${num(v)} MB` },
  { key: 'err', label: 'Estimated error rate', group: 'Reliability', better: 'lower', value: (p) => p.predictions.reliability?.estimated_error_rate_pct, format: (v) => fmtPct(v), radarLabel: 'Error rate' },
  { key: 'avail', label: 'Availability score', group: 'Reliability', better: 'higher', value: (p) => p.predictions.reliability?.availability_score, format: (v) => fmtPct(v) },
  { key: 'maxrps', label: 'Max supported throughput', group: 'Scalability', better: 'higher', value: (p) => p.predictions.scalability?.max_supported_rps, format: fmtRps },
  { key: 'headroom', label: 'Scalability headroom', group: 'Scalability', better: 'higher', value: (p) => p.predictions.scalability?.scalability_headroom_multiplier, format: (v) => `${num(v, 2)}x`, radarLabel: 'Scalability headroom' },
]

export function bestValue(values: number[], better: Better): number {
  return better === 'lower' ? Math.min(...values) : Math.max(...values)
}

/**
 * Score a value from 0 to 100 relative to the best value among the compared
 * architectures. The best one gets 100; the others are the ratio to the best.
 * This is a relative picture of the architectures being compared, NOT an
 * absolute rating, and it never invents a zero for the worst one the way
 * min-max scaling would.
 */
export function relativeScore(v: number, best: number, better: Better): number {
  if (better === 'higher') return best <= 0 ? 100 : (v / best) * 100
  if (v <= 0) return 100 // a value of 0 on a "lower is better" metric is the best possible
  return (best / v) * 100
}

export type RadarRow = { axis: string } & Record<string, string | number>

export interface RadarResult {
  rows: RadarRow[]
  /** Radar axes left out because at least one architecture has no value for them. */
  skipped: string[]
}

export function buildRadar(predictions: PredictionResult[]): RadarResult {
  const rows: RadarRow[] = []
  const skipped: string[] = []
  for (const m of METRICS) {
    if (!m.radarLabel) continue
    const values = predictions.map((p) => m.value(p))
    if (values.some((v) => v === undefined)) {
      skipped.push(m.radarLabel)
      continue
    }
    const nums = values as number[]
    const best = bestValue(nums, m.better)
    const row: RadarRow = { axis: m.radarLabel }
    predictions.forEach((p, i) => {
      row[p.architecture_id] = Math.round(relativeScore(nums[i], best, m.better) * 10) / 10
    })
    rows.push(row)
  }
  return { rows, skipped }
}

// Same colour for the same architecture on every page; chosen to stay distinguishable.
export const ARCH_COLORS = ['#0f766e', '#c2410c', '#4f46e5', '#be123c', '#475569']
export const colorFor = (index: number) => ARCH_COLORS[index % ARCH_COLORS.length]
