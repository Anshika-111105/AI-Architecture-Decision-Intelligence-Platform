import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { usePredictions } from '../features/predictions/usePredictions'

export default function PredictionDashboard() {
  const { data, isLoading, error } = usePredictions()

  if (isLoading) return <p>Loading predictions...</p>
  if (error) return <p className="text-red-600">Could not load predictions: {error.message}</p>
  if (!data?.length) return <p>No predictions yet.</p>

  // Reshape the nested API response into flat rows that Recharts can plot.
  const latencyRows = data.map((p) => ({
    architecture: p.architecture_id,
    p50: p.predictions.latency.p50_ms,
    p95: p.predictions.latency.p95_ms,
    p99: p.predictions.latency.p99_ms,
  }))

  return (
    <div>
      <h1 className="text-2xl font-semibold">Prediction Dashboard</h1>
      <section className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 font-medium">Predicted latency (ms)</h2>
        <div className="h-72">
          <ResponsiveContainer>
            <BarChart data={latencyRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="architecture" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="p50" fill="#64748b" />
              <Bar dataKey="p95" fill="#0f766e" />
              <Bar dataKey="p99" fill="#b45309" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
      <section className="mt-6 grid gap-4 sm:grid-cols-3">
        {data.map((p) => (
          <div key={p.architecture_id} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="font-medium">{p.architecture_id}</div>
            <div className="mt-2 text-sm">Cost: ${p.predictions.cost.estimated_monthly_usd.toFixed(0)}/mo</div>
            <div className="mt-2 flex gap-2 text-xs">
              <span className={`rounded px-2 py-1 ${p.sla_compliance.meets_latency_sla ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                Latency SLA {p.sla_compliance.meets_latency_sla ? 'met' : 'missed'}
              </span>
              <span className={`rounded px-2 py-1 ${p.sla_compliance.meets_budget_sla ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                Budget {p.sla_compliance.meets_budget_sla ? 'met' : 'over'}
              </span>
            </div>
          </div>
        ))}
      </section>
    </div>
  )
}
