import { fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import { handlers } from '../mocks/handlers'
import WhatIfAnalysis from './WhatIfAnalysis'

const server = setupServer(...handlers)
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderPage() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <WhatIfAnalysis />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('WhatIfAnalysis', () => {
  it('starts from the README example and lists what changed', async () => {
    renderPage()
    const changed = await screen.findByRole('region', { name: 'What changed' })
    expect(within(changed).getByText('Requests per second: 5,000 to 20,000')).toBeInTheDocument()
    expect(within(changed).getByText('Replicas: 3 to 6')).toBeInTheDocument()
    expect(screen.getByText('Data origin: simulated')).toBeInTheDocument()
  })

  it('labels each metric change as better or worse using that metric\'s direction', async () => {
    renderPage()
    await screen.findByRole('region', { name: 'What changed' })
    // 4x the load on 2x the replicas: more throughput (better), but slower and dearer (worse)
    expect(within(screen.getByRole('row', { name: /Predicted throughput/ })).getByText('better')).toBeInTheDocument()
    expect(within(screen.getByRole('row', { name: /Latency p95/ })).getByText('worse')).toBeInTheDocument()
    expect(within(screen.getByRole('row', { name: /Estimated monthly cost/ })).getByText('worse')).toBeInTheDocument()
  })

  it('resets the what-if scenario to the current one', async () => {
    renderPage()
    await screen.findByRole('region', { name: 'What changed' })
    fireEvent.click(screen.getByRole('button', { name: 'Reset to current' }))
    expect(await screen.findByText(/Nothing yet/, {}, { timeout: 3000 })).toBeInTheDocument()
    expect(within(screen.getByRole('row', { name: /Latency p95/ })).getByText('no change')).toBeInTheDocument()
  })

  it('warns when the what-if load saturates the system', async () => {
    renderPage()
    await screen.findByRole('region', { name: 'What changed' })
    const form = screen.getByRole('region', { name: 'What-if scenario' })
    fireEvent.change(within(form).getByLabelText('Requests per second'), { target: { value: '50000' } })
    expect(await screen.findByText(/almost fully used/, {}, { timeout: 3000 })).toBeInTheDocument()
  })

  it('shows an error when the model cannot be reached', async () => {
    server.use(http.post('/api/v1/what-if', () => new HttpResponse(null, { status: 500 })))
    renderPage()
    expect(await screen.findByText(/Could not calculate/)).toBeInTheDocument()
  })
})
