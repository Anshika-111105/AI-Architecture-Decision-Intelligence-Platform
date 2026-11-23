import { useState } from 'react'
import { Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts'
import ChartCard from '../components/ChartCard'
import MetricsTable from '../features/predictions/MetricsTable'
import { buildRadar, colorFor } from '../features/predictions/metrics'
import { usePredictions } from '../features/predictions/usePredictions'

const MAX_COMPARED = 3

export default function ArchitectureComparison() {
  const { data, isLoading, error } = usePredictions()
  // null means "the user has not chosen yet", so we show the first few by default.
  const [picked, setPicked] = useState<string[] | null>(null)

  if (isLoading) return <p>Loading predictions...</p>
  if (error) return <p className="text-red-600">Could not load predictions: {error.message}</p>
  if (!data?.length) return <p>No predictions yet. Run a prediction first.</p>

  const ids = data.map((p) => p.architecture_id)
  const selectedIds = picked ?? ids.slice(0, MAX_COMPARED)
  const selected = data.filter((p) => selectedIds.includes(p.architecture_id))
  const atLimit = selected.length >= MAX_COMPARED

  const toggle = (id: string) =>
    setPicked(selectedIds.includes(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id])

  const radar = buildRadar(selected)

  return (
    <div>
      <h1 className="text-2xl font-semibold">Architecture Comparison</h1>
      <p className="mt-2 text-sm text-slate-600">
        Compare two or three architectures side by side. Values are model estimates, not measured results.
      </p>

      <fieldset className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <legend className="px-1 text-sm font-medium">Architectures to compare (choose 2 or 3)</legend>
        <div className="flex flex-wrap gap-x-6 gap-y-2">
          {data.map((p, i) => {
            const checked = selectedIds.includes(p.architecture_id)
            return (
              <label key={p.architecture_id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={!checked && atLimit}
                  onChange={() => toggle(p.architecture_id)}
                />
                <span className="inline-block h-3 w-3 rounded-sm" style={{ backgroundColor: colorFor(i) }} aria-hidden="true" />
                {p.architecture_id}
              </label>
            )
          })}
        </div>
        {atLimit && data.length > MAX_COMPARED && (
          <p className="mt-2 text-xs text-slate-500">Up to {MAX_COMPARED} at a time. Untick one to choose another.</p>
        )}
      </fieldset>

      {selected.length < 2 ? (
        <p role="status" className="mt-6 rounded border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-600">
          Select at least two architectures to compare.
        </p>
      ) : (
        <>
          <section className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="mb-2 font-medium">Side by side</h2>
            <MetricsTable predictions={selected} />
          </section>

          <div className="mt-6">
            <ChartCard
              title="Relative strengths"
              caption="100 is the best of the selected architectures on that axis; the others are shown as a share of it. Lower latency, cost, CPU use and error rate score higher. This compares only the architectures chosen above; it is not an absolute rating."
              heightClass="h-96"
            >
              {radar.rows.length >= 3 ? (
                <ResponsiveContainer>
                  <RadarChart data={radar.rows}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="axis" />
                    <PolarRadiusAxis angle={60} domain={[0, 100]} tick={{ fontSize: 10 }} />
                    {selected.map((p) => (
                      <Radar
                        key={p.architecture_id}
                        name={p.architecture_id}
                        dataKey={p.architecture_id}
                        stroke={colorFor(ids.indexOf(p.architecture_id))}
                        fill={colorFor(ids.indexOf(p.architecture_id))}
                        fillOpacity={0.15}
                      />
                    ))}
                    <Legend itemSorter={null} formatter={(name) => <span style={{ color: '#334155' }}>{name}</span>} />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-slate-600">Not enough shared metrics to draw the radar chart.</p>
              )}
            </ChartCard>
            {radar.skipped.length > 0 && (
              <p className="mt-2 text-xs text-slate-500">Left out of the radar (missing for at least one architecture): {radar.skipped.join(', ')}.</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
