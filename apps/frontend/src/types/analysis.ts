import type { RequirementsForm } from './requirements.zod'

type Nullable<T> = { [K in keyof T]?: T[K] | null }

// Mirrors RequirementAnalysisResponse in ml/src/requirements/schemas.py.
export interface RequirementAnalysisResponse {
  requirements: Nullable<Omit<RequirementsForm, 'domain'>> & {
    domain?: string | null
    workload_type?: string | null
  }
  missing_fields: string[]
  assumptions: string[]
  is_complete: boolean
  raw_input?: string | null
}