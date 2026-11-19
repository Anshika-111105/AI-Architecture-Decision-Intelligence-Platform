import { NavLink, Outlet } from 'react-router-dom'
import { appRoutes } from '../routes'
import { USE_MOCKS } from '../lib/api'

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-64 shrink-0 border-r border-slate-200 bg-white p-4">
        <div className="mb-6 text-lg font-bold">ADIP</div>
        <nav className="flex flex-col gap-1">
          {appRoutes.map((r) => (
            <NavLink
              key={r.path}
              to={r.path}
              end
              className={({ isActive }) =>
                `rounded px-3 py-2 text-sm ${isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'}`
              }
            >
              {r.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8">
        {USE_MOCKS && (
          <div className="mb-6 rounded border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
            Mock data: values are invented for UI development, not model output.
          </div>
        )}
        <Outlet />
      </main>
    </div>
  )
}
