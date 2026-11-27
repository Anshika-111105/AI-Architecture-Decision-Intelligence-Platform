import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import type { Scenario, WhatIfResponse } from '../../types/proposed'

export function useWhatIf(scenario: Scenario) {
  return useQuery({
    queryKey: ['what-if', scenario],
    queryFn: () => api<WhatIfResponse>('/what-if', { method: 'POST', body: JSON.stringify({ scenario }) }),
    placeholderData: keepPreviousData,
  })
}
