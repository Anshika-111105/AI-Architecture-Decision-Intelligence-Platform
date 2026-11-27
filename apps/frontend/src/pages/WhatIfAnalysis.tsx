import { useState } from 'react'
import ChartCard from '../components/ChartCard'
import DataOriginBadge from '../components/DataOriginBadge'
import GroupedBars from '../components/GroupedBars'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { deltaOf } from '../features/whatif/deltas'
import { BASELINE, changedFields, README_WHATIF } from '../features/whatif/model'
import ScenarioForm from '../features/whatif/ScenarioForm'
import { useWhatIf } from '../features/whatif/useWhatIf'
import { fmtMs, METRICS } from '../features/predictions/metrics'
import type { PredictionResult } from '../types'
import type { Scenario } from '../types/proposed'

// The metrics README section 23 says to recalculate.
const SHOWN = ['p50', 'p95', 'p99', 'rps', 'cpu', 'mem', 'cost']
const ROWS = METRICS.filter((m) => SHOWN.includes(m.key))

const VERDICT_STYLE = { better: 'text-green-800', worse: 'text-red-700', same: 'text-slate-600' }

export default function WhatIfAnalysis() {
  const [baseline, setBaseline] = useState<Scenario>(BASELINE)
  const [scenario, setScenario] = useState<Scenario>(README_WHATIF)
  // Sliders move instantly; the model is only asked once the user pauses.
  const current = useWhatIf(useDebouncedValue(baseline, 300))
  const whatIf = useWhatIf(useDebouncedValue(scenario, 300))

  const error = current.error ?? whatIf.error
  const c = current.data
  const w = whatIf.data
  // The metric readers only look at .predictions, so a what-if result can reuse them.
  const read = (m: (typeof ROWS)[number], d: NonNullable<typeof c>) => m.value({ predictions: d.predictions } as PredictionResult)

  return (
    <div className="max-w-5xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">What-If Analysis</h1>
        {w && <DataOriginBadge origin={w.data_origin} />}
      </div>
      <p className="mt-2 text-sm text-slate-600">
        Change the load or the setup and see how the predictions move. It starts from the README example: 5,000 requests per second on 3 replicas, versus 20,000 on 6.
      </p>

      <section aria-label="What-if scenario" className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-medium">What if...</h2>
          <button type="button" onClick={() => setScenario(baseline)} className="rounded border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100">
            Reset to current
          </button>
        </div>
        <ScenarioForm idPrefix="whatif" value={scenario} onChange={setScenario} />
      </section>

      {error && <p role="alert" className="mt-6 text-red-600">Could not calculate: {error.message}</p>}
      {!error && !(c && w) && <p className="mt-6">Calculating...</p>}

      {c && w && (
        <>
          <p role="status" className="mt-3 text-xs text-slate-500">{current.isFetching || whatIf.isFetching ? 'Updating...' : ' '}</p>

          <section aria-label="What changed" className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="font-medium">What changed</h2>
            {changedFields(c.scenario, w.scenario).length === 0 ? (
              <p className="mt-2 text-sm text-slate-600">Nothing yet. The what-if scenario is the same as the current one.</p>
            ) : (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                {changedFields(c.scenario, w.scenario).map((f) => (
                  <li key={f.key}>{f.label}: {f.from} to {f.to}</li>
                ))}
              </ul>
            )}
            {w.predictions.resources.cpu_utilization_pct >= 90 && (
              <p role="status" className="mt-3 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                At this load the CPU is almost fully used. Latency estimates rise very quickly near saturation, so treat them with extra caution.
              </p>
            )}
          </section>

          <div className="mt-6">
            <ChartCard title="Predicted latency" caption="Response time percentiles in milliseconds. Lower is better.">
              <GroupedBars
                xKey="label"
                format={fmtMs}
                series={[
                  { key: 'current', name: 'Current', color: '#64748b' },
                  { key: 'whatif', name: 'What-if', color: '#0f766e' },
                ]}
                rows={(['p50_ms', 'p90_ms', 'p95_ms', 'p99_ms'] as const).map((k) => ({
                  label: k.replace('_ms', ''),
                  current: c.predictions.latency[k],
                  whatif: w.predictions.latency[k],
                }))}
              />
            </ChartCard>
          </div>

          <section className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="font-medium">Current against what-if</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-600">
                    <th className="py-2 pr-4 font-medium">Metric</th>
                    <th className="px-3 py-2 text-right font-medium">Current</th>
                    <th className="px-3 py-2 text-right font-medium">What-if</th>
                    <th className="py-2 pl-3 font-medium">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {ROWS.map((m) => {
                    const a = read(m, c)
                    const b = read(m, w)
                    if (a === undefined || b === undefined) return null
                    const d = deltaOf(a, b, m.better)
                    return (
                      <tr key={m.key} className="border-t border-slate-100">
                        <th scope="row" className="py-2 pr-4 text-left font-normal text-slate-600">{m.label}</th>
                        <td className="px-3 py-2 text-right tabular-nums">{m.format(a)}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{m.format(b)}</td>
                        <td className="py-2 pl-3">
                          {d.verdict === 'same' ? (
                            <span className={VERDICT_STYLE.same}>no change</span>
                          ) : (
                            <>
                              {d.abs > 0 ? '+' : '-'}{m.format(Math.abs(d.abs))}
                              {d.pct !== null && ` (${d.pct > 0 ? '+' : '-'}${Math.abs(d.pct).toFixed(0)}%)`}{' '}
                              <span className={VERDICT_STYLE[d.verdict]}>{d.verdict}</span>
                            </>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-xs text-slate-500">&quot;Better&quot; and &quot;worse&quot; follow each metric: lower latency, CPU, memory and cost are better; higher throughput is better.</p>
          </section>
        </>
      )}

      <details className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-medium">Edit the current scenario</summary>
        <section aria-label="Current scenario" className="mt-4">
          <ScenarioForm idPrefix="current" value={baseline} onChange={setBaseline} />
        </section>
      </details>
    </div>
  )
}
