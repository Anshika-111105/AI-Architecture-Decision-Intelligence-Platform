import SliderField from '../../components/SliderField'
import type { Scenario } from '../../types/proposed'
import { SELECTS, SLIDERS } from './model'

// Every adjustable setting from README section 23, as sliders and dropdowns.
export default function ScenarioForm({
  idPrefix,
  value,
  onChange,
}: {
  idPrefix: string
  value: Scenario
  onChange: (next: Scenario) => void
}) {
  return (
    <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
      {SLIDERS.map((f) => (
        <SliderField
          key={f.key}
          id={`${idPrefix}-${f.key}`}
          label={f.label}
          value={value[f.key]}
          min={f.min}
          max={f.max}
          step={f.step}
          format={f.format}
          onChange={(v) => onChange({ ...value, [f.key]: v })}
        />
      ))}
      {SELECTS.map((f) => (
        <div key={f.key}>
          <label htmlFor={`${idPrefix}-${f.key}`} className="block text-sm font-medium">{f.label}</label>
          <select
            id={`${idPrefix}-${f.key}`}
            value={value[f.key]}
            onChange={(e) => onChange({ ...value, [f.key]: e.target.value })}
            className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
          >
            {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
      ))}
    </div>
  )
}
