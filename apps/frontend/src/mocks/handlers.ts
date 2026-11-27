import { http, HttpResponse } from 'msw'
import type { RequirementAnalysisResponse } from '../types/analysis'
import { EXPLAIN_TARGETS, type ExplainTarget, type Scenario, type WhatIfResponse, type Weights } from '../types/proposed'
import { mockExplanation } from './explanations'
import { MOCK_PREDICTIONS } from './predictions'
import { mockRecommend } from './recommend'
import { mockWhatIfPredictions } from './whatifModel'

export { MOCK_PREDICTIONS }

// MOCK: always returns the same parse, whatever text was sent. The real
// extractor lives in ml/src/requirements/extractor.py.
const mockAnalysis: RequirementAnalysisResponse = {
  requirements: {
    domain: 'ecommerce',
    users: 100000,
    concurrency: 5000,
    rps: 500,
    peak_rps: 2000,
    latency_sla: 200,
    budget: 5000,
  },
  missing_fields: ['data_size', 'read_write_ratio', 'availability_sla'],
  assumptions: ['MOCK RESPONSE: values are fixed example data, not parsed from your text.'],
  is_complete: false,
}

export const handlers = [
  http.post('/api/v1/requirements/analyze', () => HttpResponse.json(mockAnalysis)),
  http.post('/api/v1/requirements', async ({ request }) =>
    HttpResponse.json(await request.json(), { status: 201 }),
  ),
  http.post('/api/v1/architectures', async ({ request }) =>
    HttpResponse.json(await request.json(), { status: 201 }),
  ),
  http.get('/api/v1/predictions', () => HttpResponse.json(MOCK_PREDICTIONS)),

  http.post('/api/v1/recommendations', async ({ request }) => {
    const { weights } = (await request.json()) as { weights: Weights }
    try {
      return HttpResponse.json(mockRecommend(weights, MOCK_PREDICTIONS))
    } catch (e) {
      return HttpResponse.json({ detail: e instanceof Error ? e.message : 'Invalid weights' }, { status: 422 })
    }
  }),

  http.get('/api/v1/explanations', ({ request }) => {
    const params = new URL(request.url).searchParams
    const target = params.get('target') as ExplainTarget | null
    const known = target !== null && (EXPLAIN_TARGETS as readonly string[]).includes(target)
    const body = known ? mockExplanation(params.get('architecture_id') ?? '', target) : undefined
    return body ? HttpResponse.json(body) : HttpResponse.json({ detail: 'Unknown architecture or target' }, { status: 404 })
  }),

  http.post('/api/v1/what-if', async ({ request }) => {
    const { scenario } = (await request.json()) as { scenario: Scenario }
    const body: WhatIfResponse = { scenario, predictions: mockWhatIfPredictions(scenario), data_origin: 'simulated' }
    return HttpResponse.json(body)
  }),
]
