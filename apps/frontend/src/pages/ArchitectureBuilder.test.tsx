import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { setupServer } from 'msw/node'
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { handlers } from '../mocks/handlers'
import ArchitectureBuilder from './ArchitectureBuilder'

// jsdom has no layout engine, so React Flow needs a few browser APIs stubbed.
class ResizeObserverStub {
  private cb: ResizeObserverCallback
  constructor(cb: ResizeObserverCallback) {
    this.cb = cb
  }
  observe(target: Element) {
    this.cb([{ target } as ResizeObserverEntry], this as unknown as ResizeObserver)
  }
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver
globalThis.DOMMatrixReadOnly = class {
  m22 = 1
} as unknown as typeof DOMMatrixReadOnly
Object.defineProperties(HTMLElement.prototype, {
  offsetHeight: { get: () => 100 },
  offsetWidth: { get: () => 100 },
})
;(SVGElement.prototype as unknown as { getBBox: () => object }).getBBox = () => ({ x: 0, y: 0, width: 0, height: 0 })

const server = setupServer(...handlers)
beforeAll(() => server.listen())
afterAll(() => server.close())
beforeEach(() => localStorage.clear())

function renderPage() {
  return render(
    <MemoryRouter>
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ArchitectureBuilder />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('ArchitectureBuilder', () => {
  it('starts empty and explains what is missing', () => {
    renderPage()
    expect(screen.getByText(/Add at least one Service node/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save architecture' })).toBeDisabled()
  })

  it('adds components from the palette and counts them', () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: '+ Service' }))
    fireEvent.click(screen.getByRole('button', { name: '+ Database' }))
    expect(screen.getByText(/1 services, database postgres, cache none, messaging none, 2 nodes, 0 edges/)).toBeInTheDocument()
  })

  it('loads the README example, then saves once it has a name', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Load README example' }))
    expect(screen.getByText(/1 services, database postgres, cache redis, messaging kafka, 6 nodes, 5 edges/)).toBeInTheDocument()
    const save = screen.getByRole('button', { name: 'Save architecture' })
    expect(save).toBeEnabled() // the example fills in a default name
    fireEvent.change(screen.getByLabelText('Name', { selector: '#archName' }), { target: { value: '' } })
    expect(save).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Name', { selector: '#archName' }), { target: { value: 'Shop v1' } })
    fireEvent.click(save)
    expect(await screen.findByText(/Architecture saved/)).toBeInTheDocument()
  })
})
