import type { DataOrigin } from '../types'

// Research-integrity rule (README section 45): always say where numbers come from, so
// simulated results are never mistaken for real-world measurements.
export default function DataOriginBadge({ origin }: { origin: DataOrigin }) {
  return (
    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
      Data origin: {origin}
    </span>
  )
}
