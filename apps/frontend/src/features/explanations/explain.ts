import { fmtMs, fmtUsd } from '../predictions/metrics'
import type { ExplainTarget, ExplanationResponse, FeatureContribution } from '../../types/proposed'

export const TARGETS: Record<ExplainTarget, { label: string; noun: string; format: (v: number) => string }> = {
  latency_p95_ms: { label: 'Latency (p95)', noun: 'p95 latency', format: fmtMs },
  monthly_cost_usd: { label: 'Monthly cost', noun: 'monthly cost', format: fmtUsd },
}

const formatValue = (v: FeatureContribution['feature_value']): string => {
  if (v === null) return ''
  if (typeof v === 'number') return v.toLocaleString('en-US')
  if (typeof v === 'boolean') return v ? 'yes' : 'no'
  return v
}

export const featureLabel = (c: FeatureContribution): string => {
  const value = formatValue(c.feature_value)
  return value ? `${c.feature} = ${value}` : c.feature
}

/**
 * SHAP values are additive: base value + all contributions = the prediction. If the
 * response lists only some features, this is what the unlisted ones add up to.
 */
export function residual(e: ExplanationResponse): number {
  const listed = e.contributions.reduce((s, c) => s + c.shap_value, 0)
  const r = e.prediction - e.base_value - listed
  return Math.abs(r) < 1e-6 ? 0 : r
}

export interface ChartRow {
  label: string
  /** Contribution when it raises the prediction, else 0 (so the two can be two coloured bar series). */
  raises: number
  /** Contribution when it lowers the prediction, else 0. */
  lowers: number
}

/** The `topN` strongest features by absolute effect, with everything else combined into one row. */
export function chartRows(e: ExplanationResponse, topN = 8): ChartRow[] {
  const sorted = [...e.contributions].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
  const top = sorted.slice(0, topN)
  const rest = sorted.slice(topN).reduce((s, c) => s + c.shap_value, 0) + residual(e)
  const rows: ChartRow[] = top.map((c) => ({ label: featureLabel(c), raises: Math.max(c.shap_value, 0), lowers: Math.min(c.shap_value, 0) }))
  if (rest !== 0 || sorted.length > topN) {
    rows.push({ label: 'All other features', raises: Math.max(rest, 0), lowers: Math.min(rest, 0) })
  }
  return rows
}

/** Plain-language sentence for one contribution, e.g. "rps = 5,000 raises the predicted p95 latency by 28 ms". */
export function describe(c: FeatureContribution, target: ExplainTarget): string {
  const t = TARGETS[target]
  const verb = c.shap_value >= 0 ? 'raises' : 'lowers'
  return `${featureLabel(c)} ${verb} the predicted ${t.noun} by ${t.format(Math.abs(c.shap_value))}`
}
