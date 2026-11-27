import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartCard from '../components/ChartCard'
import DataOriginBadge from '../components/DataOriginBadge'
import { chartRows, describe, residual, TARGETS } from '../features/explanations/explain'
import { useExplanation } from '../features/explanations/useExplanation'
import { fmtSigned } from '../features/predictions/metrics'
import { usePredictions } from '../features/predictions/usePredictions'
import { EXPLAIN_TARGETS, type ExplainTarget } from '../types/proposed'

export default function ShapExplanation() {
  const predictions = usePredictions()
  const [arch, setArch] = useState<string>()
  const [target, setTarget] = useState<ExplainTarget>('latency_p95_ms')
  const archId = arch ?? predictions.data?.[0]?.architecture_id
  const { data, isLoading, error } = useExplanation(archId, target)
  const t = TARGETS[target]

  return (
    <div className="max-w-5xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">SHAP Explanation</h1>
        {data && <DataOriginBadge origin={data.data_origin} />}
      </div>
      <p className="mt-2 text-sm text-slate-600">
        Which inputs pushed the model&apos;s prediction up or down? Each bar is one feature&apos;s contribution.
      </p>

      <div className="mt-6 flex flex-wrap gap-4">
        <div>
          <label htmlFor="shap-arch" className="block text-sm font-medium">Architecture</label>
          <select id="shap-arch" value={archId ?? ''} onChange={(e) => setArch(e.target.value)} className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5 text-sm">
            {(predictions.data ?? []).map((p) => <option key={p.architecture_id} value={p.architecture_id}>{p.architecture_id}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="shap-target" className="block text-sm font-medium">What to explain</label>
          <select id="shap-target" value={target} onChange={(e) => setTarget(e.target.value as ExplainTarget)} className="mt-1 rounded border border-slate-300 bg-white px-2 py-1.5 text-sm">
            {EXPLAIN_TARGETS.map((x) => <option key={x} value={x}>{TARGETS[x].label}</option>)}
          </select>
        </div>
      </div>

      {predictions.error && <p role="alert" className="mt-6 text-red-600">Could not load architectures: {predictions.error.message}</p>}
      {isLoading && <p className="mt-6">Loading explanation...</p>}
      {error && <p role="alert" className="mt-6 text-red-600">Could not load the explanation: {error.message}</p>}

      {data && (
        <>
          <p className="mt-6 text-sm">
            The model&apos;s average {t.noun} is <strong>{t.format(data.base_value)}</strong>. For <strong>{data.architecture_id}</strong> it predicts{' '}
            <strong>{t.format(data.prediction)}</strong>. The features below account for the difference.
          </p>

          <div className="mt-4">
            <ChartCard title={`What moved the ${t.noun}`} caption="Orange bars push the prediction up, blue bars push it down. Longer bars matter more." heightClass="h-96">
              <ResponsiveContainer>
                <BarChart data={chartRows(data)} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" domain={['auto', 'auto']} tickFormatter={(v: number) => fmtSigned(v, '').replace(/^\+/, '')} />
                  <YAxis type="category" dataKey="label" width={160} interval={0} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(v) => (typeof v === 'number' ? `${v >= 0 ? '+' : '-'}${t.format(Math.abs(v))}` : String(v))} />
                  <Legend itemSorter={null} formatter={(name) => <span style={{ color: '#334155' }}>{name}</span>} />
                  <ReferenceLine x={0} stroke="#64748b" />
                  <Bar dataKey="raises" name="Raises the prediction" stackId="s" fill="#c2410c" isAnimationActive={false} />
                  <Bar dataKey="lowers" name="Lowers the prediction" stackId="s" fill="#2563eb" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          <section className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="font-medium">In plain words</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
              {[...data.contributions]
                .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
                .slice(0, 5)
                .map((c) => <li key={c.feature}>{describe(c, target)}</li>)}
            </ul>
            <p className="mt-3 text-xs text-slate-500">
              Start at the average ({t.format(data.base_value)}), add every feature&apos;s push, and you reach the prediction ({t.format(data.prediction)}).
              {residual(data) !== 0 && ` Features not listed contribute ${residual(data) > 0 ? '+' : '-'}${t.format(Math.abs(residual(data)))} in total.`}
            </p>
            <p className="mt-2 text-xs text-slate-500">
              SHAP explains how the <em>model</em> reached its number, not what would happen in a real system. Treat it as a hint about where to look, not proof of cause.
            </p>
          </section>
        </>
      )}
    </div>
  )
}
