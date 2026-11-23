import { fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import { handlers, MOCK_PREDICTIONS } from '../mocks/handlers'
import ArchitectureComparison from './ArchitectureComparison'

const server = setupServer(...handlers)
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderPage() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ArchitectureComparison />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('ArchitectureComparison', () => {
  it('compares all three by default and tags the best value per row', async () => {
    renderPage()
    expect(await screen.findByRole('checkbox', { name: 'monolith' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'modular_monolith' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'microservices' })).toBeChecked()

    const p95 = screen.getByRole('row', { name: /Latency p95/ })
    expect(within(p95).getByText('115 ms').nextSibling).toHaveTextContent('best') // microservices is fastest
    const cost = screen.getByRole('row', { name: /Estimated monthly cost/ })
    expect(within(cost).getByText('$1,800').nextSibling).toHaveTextContent('best') // monolith is cheapest
  })

  it('asks for at least two architectures when fewer are ticked', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('checkbox', { name: 'monolith' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'modular_monolith' }))
    expect(screen.getByText('Select at least two architectures to compare.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('limits the comparison to three and frees a slot when one is unticked', async () => {
    const four = [...MOCK_PREDICTIONS, { ...structuredClone(MOCK_PREDICTIONS[0]), architecture_id: 'serverless' }]
    server.use(http.get('/api/v1/predictions', () => HttpResponse.json(four)))
    renderPage()
    const fourth = await screen.findByRole('checkbox', { name: 'serverless' })
    expect(fourth).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox', { name: 'monolith' }))
    expect(fourth).toBeEnabled()
  })

  it('shows n/a, not a wrong number, when an optional metric is missing', async () => {
    const partial = structuredClone(MOCK_PREDICTIONS)
    delete partial[0].predictions.scalability
    server.use(http.get('/api/v1/predictions', () => HttpResponse.json(partial)))
    renderPage()
    const row = await screen.findByRole('row', { name: /Max supported throughput/ })
    expect(within(row).getByText('n/a')).toBeInTheDocument()
    expect(screen.getByText(/Left out of the radar.*Scalability headroom/)).toBeInTheDocument()
  })
})
