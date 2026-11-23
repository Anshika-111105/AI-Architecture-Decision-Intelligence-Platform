import type { PredictionResult } from '../../types'
import { bestValue, fmtSigned, fmtUsd, GROUPS, METRICS } from './metrics'

function Verdict({ ok, margin }: { ok: boolean; margin?: string }) {
  // Text plus colour, never colour alone.
  return (
    <span className={ok ? 'text-green-800' : 'text-red-700'}>
      {ok ? 'Met' : 'Missed'}
      {margin && <span className="ml-1 text-xs text-slate-500">({margin})</span>}
    </span>
  )
}

// Side-by-side numbers for any set of architectures. The best value in each row is
// tagged "best" (only when the values actually differ), so trade-offs are visible
// instead of hidden behind a single score.
export default function MetricsTable({ predictions }: { predictions: PredictionResult[] }) {
  const cols = predictions.length + 1
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="py-2 pr-4 text-left font-medium">Metric</th>
            {predictions.map((p) => (
              <th key={p.architecture_id} className="px-3 py-2 text-right font-medium">{p.architecture_id}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {GROUPS.map((group) => (
            <GroupRows key={group} group={group} predictions={predictions} cols={cols} />
          ))}
          <tr>
            <th colSpan={cols} className="pt-4 text-left text-xs font-medium uppercase tracking-wide text-slate-500">SLA</th>
          </tr>
          <tr className="border-t border-slate-100">
            <th scope="row" className="py-2 pr-4 text-left font-normal text-slate-600">Latency SLA</th>
            {predictions.map((p) => (
              <td key={p.architecture_id} className="px-3 py-2 text-right">
                <Verdict
                  ok={p.sla_compliance.meets_latency_sla}
                  margin={p.sla_compliance.latency_margin_ms === undefined ? undefined : fmtSigned(p.sla_compliance.latency_margin_ms, ' ms')}
                />
              </td>
            ))}
          </tr>
          <tr className="border-t border-slate-100">
            <th scope="row" className="py-2 pr-4 text-left font-normal text-slate-600">Budget</th>
            {predictions.map((p) => (
              <td key={p.architecture_id} className="px-3 py-2 text-right">
                <Verdict
                  ok={p.sla_compliance.meets_budget_sla}
                  margin={p.sla_compliance.budget_margin_usd === undefined ? undefined : `${p.sla_compliance.budget_margin_usd >= 0 ? '+' : '-'}${fmtUsd(Math.abs(p.sla_compliance.budget_margin_usd))}`}
                />
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function GroupRows({ group, predictions, cols }: { group: string; predictions: PredictionResult[]; cols: number }) {
  const metrics = METRICS.filter((m) => m.group === group)
  return (
    <>
      <tr>
        <th colSpan={cols} className="pt-4 text-left text-xs font-medium uppercase tracking-wide text-slate-500">{group}</th>
      </tr>
      {metrics.map((m) => {
        const values = predictions.map((p) => m.value(p))
        const present = values.filter((v): v is number => v !== undefined)
        const best = present.length > 0 ? bestValue(present, m.better) : undefined
        const differ = present.length >= 2 && present.some((v) => v !== present[0])
        return (
          <tr key={m.key} className="border-t border-slate-100">
            <th scope="row" className="py-2 pr-4 text-left font-normal text-slate-600">{m.label}</th>
            {values.map((v, i) => (
              <td key={predictions[i].architecture_id} className="px-3 py-2 text-right">
                {v === undefined ? (
                  <span className="text-slate-400">n/a</span>
                ) : (
                  <>
                    <span className={differ && v === best ? 'font-semibold' : ''}>{m.format(v)}</span>
                    {differ && v === best && (
                      <span className="ml-1.5 rounded bg-emerald-100 px-1 py-0.5 text-[10px] font-medium text-emerald-800">best</span>
                    )}
                  </>
                )}
              </td>
            ))}
          </tr>
        )
      })}
    </>
  )
}
