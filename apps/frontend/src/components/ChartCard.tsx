import type { ReactNode } from 'react'

// A titled box for one chart. Recharts' ResponsiveContainer fills its parent, so the
// parent needs an explicit height; that is what heightClass provides.
export default function ChartCard({
  title,
  caption,
  heightClass = 'h-64',
  children,
}: {
  title: string
  caption?: string
  heightClass?: string
  children: ReactNode
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-medium">{title}</h2>
      {caption && <p className="mt-1 text-xs text-slate-500">{caption}</p>}
      <div className={`mt-4 ${heightClass}`}>{children}</div>
    </section>
  )
}
