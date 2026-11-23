import { render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { handlers } from '../mocks/handlers'
import PredictionDashboard from './PredictionDashboard'

const server = setupServer(...handlers)
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderPage() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <PredictionDashboard />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('PredictionDashboard', () => {
  it('shows each architecture with SLA status and margins that agree with each other', async () => {
    renderPage()
    const mono = await screen.findByRole('article', { name: 'monolith' })
    expect(within(mono).getByText('Latency SLA missed (-10 ms)')).toBeInTheDocument()
    expect(within(mono).getByText('Budget met (+$3,200)')).toBeInTheDocument()

    const micro = screen.getByRole('article', { name: 'microservices' })
    expect(within(micro).getByText('Latency SLA met (+35 ms)')).toBeInTheDocument()
    expect(within(micro).getByText('Budget over (-$400)')).toBeInTheDocument()
  })

  it('offers the numbers as a table, with the best value in a row tagged', async () => {
    renderPage()
    await screen.findByRole('article', { name: 'monolith' })
    const row = screen.getByRole('row', { name: /Estimated monthly cost/ })
    expect(within(row).getByText('$1,800')).toBeInTheDocument()
    expect(within(row).getAllByText('best')).toHaveLength(1) // only the cheapest
  })

  it('says so when there are no predictions', async () => {
    server.use(http.get('/api/v1/predictions', () => HttpResponse.json([])))
    renderPage()
    expect(await screen.findByText('No predictions yet.')).toBeInTheDocument()
  })

  it('shows an error when the request fails', async () => {
    server.use(http.get('/api/v1/predictions', () => new HttpResponse(null, { status: 500 })))
    renderPage()
    expect(await screen.findByText(/Could not load predictions/)).toBeInTheDocument()
  })
})
