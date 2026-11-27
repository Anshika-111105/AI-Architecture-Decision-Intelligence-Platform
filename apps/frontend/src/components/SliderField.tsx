// A labelled range slider that shows its current value. Controlled: the parent owns the number.
export default function SliderField({
  id,
  label,
  value,
  min,
  max,
  step,
  onChange,
  format = String,
  hint,
}: {
  id: string
  label: string
  value: number
  min: number
  max: number
  step: number
  onChange: (value: number) => void
  format?: (value: number) => string
  hint?: string
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <label htmlFor={id} className="font-medium">{label}</label>
        <output htmlFor={id} className="tabular-nums text-slate-700">{format(value)}</output>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full accent-slate-900"
      />
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  )
}
