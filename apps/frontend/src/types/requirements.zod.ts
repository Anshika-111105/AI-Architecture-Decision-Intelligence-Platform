import { z } from 'zod'

// Runtime validation for the requirements form. The shape mirrors
// packages/shared-schemas/requirements.schema.json, and the two refine()
// rules mirror NormalizedRequirement in ml/src/requirements/schemas.py.
export const DOMAINS = [
  'e-commerce',
  'fintech',
  'social_network',
  'streaming',
  'iot',
  'healthcare',
  'saas',
] as const

export const requirementsSchema = z
  .object({
    project_id: z.string().min(1, 'Project id is required'),
    domain: z.enum(DOMAINS),
    users: z.number().int().min(1),
    concurrency: z.number().int().min(1),
    rps: z.number().min(0.1),
    peak_rps: z.number().min(0.1),
    data_size: z.number().min(0.01, 'Data size is in GB'),
    read_write_ratio: z.number().min(0).max(1),
    latency_sla: z.number().min(1, 'Latency SLA is in ms'),
    availability_sla: z.number().min(90).max(100),
    budget: z.number().min(10, 'Monthly budget in USD'),
    traffic_growth: z.number().min(0).optional(),
    team_size: z.number().int().min(1).optional(),
  })
  .refine((r) => r.peak_rps >= r.rps, {
    message: 'Peak RPS cannot be lower than baseline RPS',
    path: ['peak_rps'],
  })
  .refine((r) => r.concurrency <= r.users, {
    message: 'Concurrency cannot exceed total users',
    path: ['concurrency'],
  })

export type RequirementsForm = z.infer<typeof requirementsSchema>
