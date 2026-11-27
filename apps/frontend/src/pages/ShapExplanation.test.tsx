import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { setupServer } from 'msw/node'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { handlers } from '../mocks/handlers'
import ShapExplanation from './ShapExplanation'

const server = setupServer(...handlers)
beforeAll(() => server.listen())
afterAll(() => server.close())

function renderPage() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ShapExplanation />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('ShapExplanation', () => {
  it('explains the first architecture\'s latency in plain words, with the average and the prediction', async () => {
    renderPage()
    expect(await screen.findByText('rps = 5,000 raises the predicted p95 latency by 28 ms')).toBeInTheDocument()
    expect(screen.getByText('cache = redis lowers the predicted p95 latency by 12 ms')).toBeInTheDocument()
    expect(screen.getByText(/Start at the average \(140 ms\).*\(160 ms\)/)).toBeInTheDocument()
    expect(screen.getByText('Data origin: simulated')).toBeInTheDocument()
  })

  it('switches architecture', async () => {
    renderPage()
    await screen.findByText(/rps = 5,000 raises/)
    fireEvent.change(screen.getByLabelText('Architecture'), { target: { value: 'microservices' } })
    expect(await screen.findByText('network_hops = 6 raises the predicted p95 latency by 7 ms')).toBeInTheDocument()
  })

  it('switches what is explained', async () => {
    renderPage()
    await screen.findByText(/rps = 5,000 raises/)
    fireEvent.change(screen.getByLabelText('What to explain'), { target: { value: 'monthly_cost_usd' } })
    expect(await screen.findByText('replica_count = 3 raises the predicted monthly cost by $120')).toBeInTheDocument()
  })

  it('reminds the reader that SHAP explains the model, not real-world causes', async () => {
    renderPage()
    expect(await screen.findByText(/not what would happen in a real system/)).toBeInTheDocument()
  })
})
