import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { ExplainTarget, ExplanationResponse } from '../../types/proposed'

export function useExplanation(architectureId: string | undefined, target: ExplainTarget) {
  return useQuery({
    queryKey: ['explanation', architectureId, target],
    queryFn: () =>
      api<ExplanationResponse>(`/explanations?architecture_id=${encodeURIComponent(architectureId ?? '')}&target=${target}`),
    enabled: Boolean(architectureId),
  })
}
