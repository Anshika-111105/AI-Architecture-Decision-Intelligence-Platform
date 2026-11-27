import { Link } from 'react-router-dom'
import ChartCard from '../components/ChartCard'
import GroupedBars, { type Series } from '../components/GroupedBars'
import MetricsTable from '../features/predictions/MetricsTable'
import { fmtMs, fmtPct, fmtRps, fmtSigned, fmtUsd } from '../features/predictions/metrics'
import { usePredictions } from '../features/predictions/usePredictions'

// Ordered percentiles use one hue getting darker, so "higher percentile" reads as "more intense".
const PERCENTILE_SERIES: Series[] = [
  { key: 'p50', name: 'p50', color: '#5eead4' },
  { key: 'p90', name: 'p90', color: '#14b8a6' },
  { key: 'p95', name: 'p95', color: '#0f766e' },
  { key: 'p99', name: 'p99', color: '#134e4a' },
]

export default function PredictionDashboard() {
  const { data, isLoading, error } = usePredictions()

  if (isLoading) return <p>Loading predictions...</p>
  if (error) return <p className="text-red-600">Could not load predictions: {error.message}</p>
  if (!data?.length) return <p>No predictions yet.</p>

  // Reshape the nested API response into flat rows (one per architecture) that Recharts can plot.
  const latencyRows = data.map((p) => ({
    architecture: p.architecture_id,
    p50: p.predictions.latency.p50_ms,
    p90: p.predictions.latency.p90_ms,
    p95: p.predictions.latency.p95_ms,
    p99: p.predictions.latency.p99_ms,
  }))
  // max_supported_rps is optional in the schema: only draw it when every architecture has it.
  const hasMaxRps = data.every((p) => p.predictions.scalability?.max_supported_rps !== undefined)
  const throughputRows = data.map((p) => ({
    architecture: p.architecture_id,
    predicted: p.predictions.throughput.predicted_rps,
    max: p.predictions.scalability?.max_supported_rps,
  }))
  const throughputSeries: Series[] = [
    { key: 'predicted', name: 'Predicted', color: '#0f766e' },
    ...(hasMaxRps ? [{ key: 'max', name: 'Max supported', color: '#94a3b8' }] : []),
  ]
  const costRows = data.map((p) => ({ architecture: p.architecture_id, cost: p.predictions.cost.estimated_monthly_usd }))
  const cpuRows = data.map((p) => ({ architecture: p.architecture_id, cpu: p.predictions.resources.cpu_utilization_pct }))
  const memRows = data.map((p) => ({ architecture: p.architecture_id, mem: p.predictions.resources.memory_utilization_mb }))

  return (
    <div>
      <h1 className="text-2xl font-semibold">Prediction Dashboard</h1>
      <p className="mt-2 text-sm text-slate-600">
        Model estimates for each architecture, not measured production results. To pick two or three side by side, use{' '}
        <Link to="/compare" className="underline">Architecture Comparison</Link>.
      </p>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <ChartCard title="Predicted latency" caption="Response time percentiles in milliseconds. Lower is better.">
            <GroupedBars rows={latencyRows} series={PERCENTILE_SERIES} format={fmtMs} />
          </ChartCard>
        </div>
        <ChartCard title="Throughput" caption="Requests per second (req/s). Higher is better.">
          <GroupedBars rows={throughputRows} series={throughputSeries} format={fmtRps} axisFormat={(v) => v.toLocaleString('en-US')} />
        </ChartCard>
        <ChartCard title="Estimated monthly cost" caption="US dollars per month. Lower is better.">
          <GroupedBars rows={costRows} series={[{ key: 'cost', name: 'Cost', color: '#c2410c' }]} format={fmtUsd} />
        </ChartCard>
        <ChartCard title="CPU utilization" caption="Share of allocated CPU in use.">
          <GroupedBars rows={cpuRows} series={[{ key: 'cpu', name: 'CPU', color: '#4f46e5' }]} format={(v) => fmtPct(v, 0)} />
        </ChartCard>
        <ChartCard title="Memory utilization" caption="Megabytes (MB) in use.">
          <GroupedBars rows={memRows} series={[{ key: 'mem', name: 'Memory', color: '#be123c' }]} format={(v) => `${v.toLocaleString('en-US')} MB`} axisFormat={(v) => v.toLocaleString('en-US')} />
        </ChartCard>
      </div>

      <section className="mt-6">
        <h2 className="font-medium">SLA compliance</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          {data.map((p) => {
            const s = p.sla_compliance
            return (
              <article key={p.architecture_id} aria-label={p.architecture_id} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="font-medium">{p.architecture_id}</div>
                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                  <span className={`rounded px-2 py-1 ${s.meets_latency_sla ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    Latency SLA {s.meets_latency_sla ? 'met' : 'missed'}
                    {s.latency_margin_ms !== undefined && ` (${fmtSigned(s.latency_margin_ms, ' ms')})`}
                  </span>
                  <span className={`rounded px-2 py-1 ${s.meets_budget_sla ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    Budget {s.meets_budget_sla ? 'met' : 'over'}
                    {s.budget_margin_usd !== undefined && ` (${s.budget_margin_usd >= 0 ? '+' : '-'}${fmtUsd(Math.abs(s.budget_margin_usd))})`}
                  </span>
                </div>
              </article>
            )
          })}
        </div>
      </section>

      <details className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-medium">Show all numbers as a table</summary>
        <div className="mt-3">
          <MetricsTable predictions={data} />
        </div>
      </details>
    </div>
  )
}
