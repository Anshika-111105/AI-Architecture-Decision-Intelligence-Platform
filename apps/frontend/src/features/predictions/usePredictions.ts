import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { PredictionResult } from '../../types'

// TanStack Query handles caching, loading and error states for us.
export function usePredictions() {
  return useQuery({
    queryKey: ['predictions'],
    queryFn: () => api<PredictionResult[]>('/predictions'),
  })
}
