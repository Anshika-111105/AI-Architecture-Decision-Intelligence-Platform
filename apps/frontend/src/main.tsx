import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'
import Layout from './components/Layout'
import { appRoutes } from './routes'
import { USE_MOCKS } from './lib/api'

const queryClient = new QueryClient()

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: appRoutes.map((r) => ({ path: r.path, element: r.element })),
  },
])

async function start() {
  if (USE_MOCKS) {
    const { worker } = await import('./mocks/browser')
    await worker.start()
  }
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </StrictMode>,
  )
}

start()
