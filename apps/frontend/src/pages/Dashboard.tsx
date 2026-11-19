import { Link } from 'react-router-dom'
import { appRoutes } from '../routes'

export default function Dashboard() {
  return (
    <div>
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <p className="mt-2 text-slate-600">Follow the workflow from requirements to a transparent architecture decision.</p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {appRoutes.slice(1).map((r) => (
          <Link key={r.path} to={r.path} className="rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400">
            <div className="font-medium">{r.label}</div>
          </Link>
        ))}
      </div>
    </div>
  )
}
