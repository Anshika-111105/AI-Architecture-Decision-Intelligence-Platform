import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export interface Series {
  key: string
  name: string
  color: string
}

// One reusable bar chart: rows are one object per group on the x axis (for example one
// per architecture), and each series picks a column to draw as a bar.
export default function GroupedBars({
  rows,
  series,
  format,
  axisFormat = format,
  xKey = 'architecture',
}: {
  rows: Record<string, string | number | undefined>[]
  series: Series[]
  format: (v: number) => string
  /** Shorter text for the y-axis ticks (the tooltip keeps the full `format`). */
  axisFormat?: (v: number) => string
  /** The row field used for the x-axis labels. */
  xKey?: string
}) {
  return (
    <ResponsiveContainer>
      <BarChart data={rows}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        {/* interval={0}: draw every label; Recharts otherwise hides labels that might overlap. */}
        <XAxis dataKey={xKey} interval={0} tick={{ fontSize: 12 }} />
        <YAxis tickFormatter={axisFormat} width={84} />
        <Tooltip formatter={(v) => (typeof v === 'number' ? format(v) : String(v))} />
        {/* Default legend text takes the series colour (unreadable for light ones) and is sorted by name. */}
        {series.length > 1 && (
          <Legend itemSorter={null} formatter={(name) => <span style={{ color: '#334155' }}>{name}</span>} />
        )}
        {series.map((s) => (
          <Bar key={s.key} dataKey={s.key} name={s.name} fill={s.color} radius={[3, 3, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
