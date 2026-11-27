import { useState } from 'react'
import { CartesianGrid, LabelList, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import ChartCard from '../components/ChartCard'
import DataOriginBadge from '../components/DataOriginBadge'
import SliderField from '../components/SliderField'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { BETTER, CRITERIA, criterionOf, DEFAULT_WEIGHTS } from '../features/recommendation/criteria'
import { paretoFront } from '../features/recommendation/pareto'
import { compareOptions, type TradeOff } from '../features/recommendation/tradeoffs'
import { useRecommendation } from '../features/recommendation/useRecommendation'
import { CRITERIA_KEYS, type CriterionKey, type RankedArchitecture, type Weights } from '../types/proposed'

const VERDICT_STYLE: Record<TradeOff['verdict'], string> = {
  better: 'text-green-800',
  worse: 'text-red-700',
  same: 'text-slate-600',
  unknown: 'text-slate-500',
}

const idealCorner = (x: CriterionKey, y: CriterionKey) =>
  `${BETTER[y] === 'lower' ? 'bottom' : 'top'}-${BETTER[x] === 'lower' ? 'left' : 'right'}`

function TradeOffs({ pick, other }: { pick: RankedArchitecture; other: RankedArchitecture }) {
  return (
    <div className="mt-4">
      <h3 className="text-sm font-medium">
        Compared with {other.architecture_id}
        {!other.feasible && <span className="font-normal text-slate-600"> ({other.violations.join(', ')})</span>}
      </h3>
      <ul className="mt-1 space-y-1 text-sm">
        {compareOptions(pick, other).map((t) => (
          <li key={t.label}>
            <span className="font-medium">{t.label}:</span> {t.pick} vs {t.other}{' '}
            <span className={VERDICT_STYLE[t.verdict]}>{t.verdict === 'unknown' ? 'n/a' : t.verdict}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function RecommendationView() {
  const [weights, setWeights] = useState<Weights>(DEFAULT_WEIGHTS)
  const [axes, setAxes] = useState<{ x: CriterionKey; y: CriterionKey }>({ x: 'cost', y: 'latency' })

  const total = CRITERIA_KEYS.reduce((s, k) => s + weights[k], 0)
  // The sliders move instantly; the API is only called once the user pauses.
  const debounced = useDebouncedValue(weights, 300)
  const debouncedTotal = CRITERIA_KEYS.reduce((s, k) => s + debounced[k], 0)
  const { data, error, isFetching } = useRecommendation(debounced, debouncedTotal > 0)

  // Choosing the axis the other one already uses swaps them, so the two always differ.
  const setAxis = (which: 'x' | 'y', key: CriterionKey) =>
    setAxes((prev) => (key === (which === 'x' ? prev.y : prev.x) ? { x: prev.y, y: prev.x } : { ...prev, [which]: key }))

  const pick = data?.ranking.find((r) => r.architecture_id === data.recommended_id)
  const runnerUp = pick ? data?.ranking.find((r) => r.architecture_id !== pick.architecture_id) : undefined

  return (
    <div className="max-w-5xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">Recommendation</h1>
        {data && <DataOriginBadge origin={data.data_origin} />}
      </div>
      <p className="mt-2 text-sm text-slate-600">
        Rank the architectures by what matters to you. Every number behind the ranking is shown, so you can see the trade-offs and not just a winner.
      </p>

      <section aria-label="Priorities" className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-medium">What matters to you</h2>
          <button type="button" onClick={() => setWeights(DEFAULT_WEIGHTS)} className="rounded border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100">
            Reset to 35 / 25 / 20 / 20
          </button>
        </div>
        <p className="mt-1 text-xs text-slate-500">Weights are scaled to add up to 100%, so only their proportions matter.</p>
        <div className="mt-4 grid gap-x-6 gap-y-4 sm:grid-cols-2">
          {CRITERIA.map((c) => (
            <SliderField
              key={c.key}
              id={`weight-${c.key}`}
              label={c.label}
              value={weights[c.key]}
              min={0}
              max={100}
              step={5}
              format={(v) => `${total > 0 ? Math.round((v / total) * 100) : 0}%`}
              hint={c.note}
              onChange={(v) => setWeights((w) => ({ ...w, [c.key]: v }))}
            />
          ))}
        </div>
      </section>

      {total === 0 && (
        <p role="alert" className="mt-6 rounded border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Set at least one weight above 0 to get a ranking.
        </p>
      )}
      {total > 0 && error && <p role="alert" className="mt-6 text-red-600">Could not get a recommendation: {error.message}</p>}
      {total > 0 && !error && !data && <p className="mt-6">Calculating ranking...</p>}

      {total > 0 && data && (
        <>
          <p role="status" className="mt-3 text-xs text-slate-500">{isFetching ? 'Updating...' : ' '}</p>

          <section aria-label="Recommendation" className="mt-2 rounded-lg border-2 border-teal-700 bg-white p-4">
            {pick ? (
              <>
                <p className="text-xs uppercase tracking-wide text-slate-500">Recommended</p>
                <h2 className="text-xl font-semibold">{pick.architecture_id}</h2>
                <p className="mt-1 text-sm text-slate-600">
                  The best-ranked option that meets your latency SLA and budget (score {pick.closeness.toFixed(2)} out of 1).
                </p>
                {pick.rank > 1 && (
                  <p className="mt-1 text-sm text-amber-800">
                    {pick.rank - 1} higher-ranked {pick.rank === 2 ? 'option was' : 'options were'} skipped because of a broken constraint. See the table.
                  </p>
                )}
                {runnerUp && <TradeOffs pick={pick} other={runnerUp} />}
              </>
            ) : (
              <p role="alert" className="text-sm text-red-700">
                No architecture meets both your latency SLA and your budget. The ranking below is for information only; relax a constraint or change the architectures.
              </p>
            )}
          </section>

          <section className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="font-medium">Ranking</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-600">
                    <th className="py-2 pr-3 font-medium">#</th>
                    <th className="py-2 pr-3 font-medium">Architecture</th>
                    <th className="py-2 pr-3 font-medium">Score</th>
                    {CRITERIA.map((c) => <th key={c.key} className="py-2 pr-3 text-right font-medium">{c.label}</th>)}
                    <th className="py-2 font-medium">Constraints</th>
                  </tr>
                </thead>
                <tbody>
                  {data.ranking.map((r) => (
                    <tr key={r.architecture_id} className={`border-t border-slate-100 ${r.architecture_id === data.recommended_id ? 'bg-teal-50' : ''}`}>
                      <td className="py-2 pr-3">{r.rank}</td>
                      <th scope="row" className="py-2 pr-3 text-left font-medium">{r.architecture_id}</th>
                      <td className="py-2 pr-3">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-24 rounded bg-slate-200" aria-hidden="true">
                            <div className="h-2 rounded bg-teal-700" style={{ width: `${Math.round(r.closeness * 100)}%` }} />
                          </div>
                          <span className="tabular-nums">{r.closeness.toFixed(2)}</span>
                        </div>
                      </td>
                      {CRITERIA.map((c) => {
                        const v = r.values[c.key]
                        return <td key={c.key} className="py-2 pr-3 text-right tabular-nums">{v === null ? <span className="text-slate-400">n/a</span> : c.metric.format(v)}</td>
                      })}
                      <td className="py-2">
                        {r.feasible ? <span className="text-green-800">Meets SLA and budget</span> : <span className="text-red-700">{r.violations.join(', ')}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {data.excluded_criteria.length > 0 && (
              <p className="mt-2 text-xs text-amber-800">
                Left out of the ranking (missing for at least one option): {data.excluded_criteria.map((k) => criterionOf(k).label).join(', ')}.
              </p>
            )}
            <p className="mt-2 text-xs text-slate-500">
              Score is TOPSIS closeness to the ideal option: 1 means best on every weighted criterion, 0 means worst. It compares only the options listed here.
            </p>
          </section>

          <ParetoSection data={data.ranking} axes={axes} setAxis={setAxis} />
        </>
      )}
    </div>
  )
}

function ParetoSection({
  data,
  axes,
  setAxis,
}: {
  data: RankedArchitecture[]
  axes: { x: CriterionKey; y: CriterionKey }
  setAxis: (which: 'x' | 'y', key: CriterionKey) => void
}) {
  const cx = criterionOf(axes.x)
  const cy = criterionOf(axes.y)
  const points = data.flatMap((r) => {
    const x = r.values[axes.x]
    const y = r.values[axes.y]
    return x === null || y === null ? [] : [{ id: r.architecture_id, x, y }]
  })
  const front = paretoFront(points, BETTER[axes.x], BETTER[axes.y])
  const onFrontier = points.filter((p) => front.has(p.id)).sort((a, b) => a.x - b.x)
  const beaten = points.filter((p) => !front.has(p.id))
  const dir = (k: CriterionKey) => (BETTER[k] === 'lower' ? 'lower is better' : 'higher is better')

  return (
    <section className="mt-6">
      <div className="mb-3 flex flex-wrap items-end gap-4">
        <h2 className="mr-auto font-medium">Trade-off view (Pareto frontier)</h2>
        {(['x', 'y'] as const).map((which) => (
          <div key={which}>
            <label htmlFor={`axis-${which}`} className="block text-xs font-medium">{which === 'x' ? 'Horizontal axis' : 'Vertical axis'}</label>
            <select id={`axis-${which}`} value={axes[which]} onChange={(e) => setAxis(which, e.target.value as CriterionKey)} className="mt-1 rounded border border-slate-300 bg-white px-2 py-1 text-sm">
              {CRITERIA.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
            </select>
          </div>
        ))}
      </div>
      <ChartCard
        title={`${cy.label} against ${cx.label}`}
        caption={`Each dot is an architecture. Teal dots are on the Pareto frontier: no other option beats them on both axes at once. The ideal corner is the ${idealCorner(axes.x, axes.y)}.`}
        heightClass="h-96"
      >
        {points.length < 2 ? (
          <p className="text-sm text-slate-600">Not enough options with both values to draw this view.</p>
        ) : (
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 20, right: 40, bottom: 30, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="x" padding={{ left: 30, right: 70 }} name={cx.label} domain={['auto', 'auto']} tickFormatter={cx.metric.format} label={{ value: `${cx.label} (${dir(axes.x)})`, position: 'insideBottom', offset: -15 }} />
              <YAxis type="number" dataKey="y" padding={{ top: 30, bottom: 20 }} name={cy.label} domain={['auto', 'auto']} tickFormatter={cy.metric.format} width={84} label={{ value: `${cy.label} (${dir(axes.y)})`, angle: -90, position: 'insideLeft', offset: -2, style: { textAnchor: 'middle' } }} />
              <Tooltip formatter={(v, name) => (typeof v === 'number' ? (name === cx.label ? cx.metric.format(v) : cy.metric.format(v)) : String(v))} />
              <Legend itemSorter={null} verticalAlign="top" formatter={(name) => <span style={{ color: '#334155' }}>{name}</span>} />
              <Scatter name="On the frontier" data={onFrontier} fill="#0f766e" line={{ stroke: '#0f766e', strokeWidth: 2 }}>
                <LabelList dataKey="id" position="top" />
              </Scatter>
              {beaten.length > 0 && (
                <Scatter name="Beaten by another option" data={beaten} fill="#94a3b8">
                  <LabelList dataKey="id" position="top" />
                </Scatter>
              )}
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </ChartCard>
    </section>
  )
}
