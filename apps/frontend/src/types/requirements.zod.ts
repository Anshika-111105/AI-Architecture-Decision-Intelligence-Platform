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

// An empty number input arrives as undefined; this gives a readable message instead of zod's default.
const num = () => z.number({ error: 'Enter a number' })

export const requirementsSchema = z
  .object({
    project_id: z.string().min(1, 'Project id is required'),
    domain: z.enum(DOMAINS),
    users: num().int().min(1),
    concurrency: num().int().min(1),
    rps: num().min(0.1),
    peak_rps: num().min(0.1),
    data_size: num().min(0.01, 'Data size is in GB'),
    read_write_ratio: num().min(0).max(1),
    latency_sla: num().min(1, 'Latency SLA is in ms'),
    availability_sla: num().min(90).max(100),
    budget: num().min(10, 'Monthly budget in USD'),
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