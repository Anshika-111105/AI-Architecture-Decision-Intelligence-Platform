import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { RecommendationResponse, Weights } from '../../types/proposed'

// POST because the weights travel in the body; it only calculates, nothing is saved.
// keepPreviousData: while a new ranking loads, keep showing the last one instead of a blank page.
export function useRecommendation(weights: Weights, enabled: boolean) {
  return useQuery({
    queryKey: ['recommendation', weights],
    queryFn: () => api<RecommendationResponse>('/recommendations', { method: 'POST', body: JSON.stringify({ weights }) }),
    enabled,
    placeholderData: keepPreviousData,
  })
}
