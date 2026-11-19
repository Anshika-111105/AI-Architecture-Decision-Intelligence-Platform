import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { setupServer } from 'msw/node'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { handlers } from '../mocks/handlers'
import PredictionDashboard from './PredictionDashboard'

// Recharts' ResponsiveContainer needs ResizeObserver, which jsdom lacks.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}

const server = setupServer(...handlers)
beforeAll(() => server.listen())
afterAll(() => server.close())

describe('PredictionDashboard', () => {
  it('loads mock predictions and shows each architecture with its SLA status', async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <PredictionDashboard />
      </QueryClientProvider>,
    )
    expect(await screen.findByText('monolith')).toBeInTheDocument()
    expect(screen.getByText('microservices')).toBeInTheDocument()
    expect(screen.getAllByText(/Latency SLA/).length).toBe(3)
  })
})
