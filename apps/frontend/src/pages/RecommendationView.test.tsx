import { fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import { handlers } from '../mocks/handlers'
import RecommendationView from './RecommendationView'

const server = setupServer(...handlers)
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderPage() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <RecommendationView />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

const setWeight = (label: string, value: number) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value: String(value) } })

describe('RecommendationView', () => {
  it('recommends the best option that meets the SLA and budget, and shows trade-offs', async () => {
    renderPage()
    const card = await screen.findByRole('region', { name: 'Recommendation' })
    expect(within(card).getByRole('heading', { name: 'modular_monolith' })).toBeInTheDocument()
    expect(within(card).getByText(/Compared with/)).toBeInTheDocument()
    expect(within(card).getByText('Cost:')).toBeInTheDocument()
    // all three candidates are listed with their constraint status
    expect(screen.getAllByRole('rowheader')).toHaveLength(3)
    expect(screen.getByText('Misses the latency SLA')).toBeInTheDocument()
    expect(screen.getByText('Over budget')).toBeInTheDocument()
  })

  it('shows the weights as shares of 100% and starts at 35 / 25 / 20 / 20', async () => {
    renderPage()
    await screen.findByRole('region', { name: 'Recommendation' })
    expect(screen.getByLabelText('Latency')).toHaveValue('35')
    expect(screen.getByLabelText('Cost')).toHaveValue('25')
    expect(screen.getByText('35%')).toBeInTheDocument()
  })

  it('re-ranks when priorities change, but never recommends an option that breaks a constraint', async () => {
    renderPage()
    await screen.findByRole('region', { name: 'Recommendation' })
    setWeight('Latency', 0)
    setWeight('Scalability', 0)
    setWeight('Reliability', 0)
    setWeight('Cost', 100)

    // cost only: the cheapest option (monolith) ranks first, but it misses the latency SLA...
    const firstRow = async () => within(screen.getByRole('table')).getAllByRole('row')[1]
    await screen.findByText(/1 higher-ranked option was skipped/, {}, { timeout: 3000 })
    expect(await firstRow()).toHaveTextContent('monolith')
    // ...so the recommendation is still the best option that satisfies the constraints
    const card = screen.getByRole('region', { name: 'Recommendation' })
    expect(within(card).getByRole('heading', { name: 'modular_monolith' })).toBeInTheDocument()
  })

  it('asks for at least one weight above 0', async () => {
    renderPage()
    await screen.findByRole('region', { name: 'Recommendation' })
    for (const label of ['Latency', 'Cost', 'Scalability', 'Reliability']) setWeight(label, 0)
    expect(screen.getByRole('alert')).toHaveTextContent('Set at least one weight above 0')
    expect(screen.queryByRole('region', { name: 'Recommendation' })).not.toBeInTheDocument()
  })

  it('resets the weights', async () => {
    renderPage()
    await screen.findByRole('region', { name: 'Recommendation' })
    setWeight('Latency', 0)
    expect(screen.getByLabelText('Latency')).toHaveValue('0')
    fireEvent.click(screen.getByRole('button', { name: /Reset to 35/ }))
    expect(screen.getByLabelText('Latency')).toHaveValue('35')
  })

  it('shows the error when the request fails', async () => {
    server.use(http.post('/api/v1/recommendations', () => HttpResponse.json({ detail: 'x' }, { status: 500 })))
    renderPage()
    expect(await screen.findByText(/Could not get a recommendation/)).toBeInTheDocument()
  })

  it('says so when no option meets the constraints', async () => {
    server.use(
      http.post('/api/v1/recommendations', () =>
        HttpResponse.json({
          method: 'topsis',
          weights_used: { latency: 0.25, cost: 0.25, scalability: 0.25, reliability: 0.25 },
          excluded_criteria: [],
          recommended_id: null,
          data_origin: 'simulated',
          ranking: [
            { architecture_id: 'a', rank: 1, closeness: 0.7, values: { latency: 1, cost: 1, scalability: 1, reliability: 1 }, feasible: false, violations: ['Over budget'] },
            { architecture_id: 'b', rank: 2, closeness: 0.3, values: { latency: 2, cost: 2, scalability: 2, reliability: 2 }, feasible: false, violations: ['Misses the latency SLA'] },
          ],
        }),
      ),
    )
    renderPage()
    expect(await screen.findByText(/No architecture meets both your latency SLA and your budget/)).toBeInTheDocument()
  })
})
