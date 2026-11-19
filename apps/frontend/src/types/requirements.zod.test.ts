import { describe, expect, it } from 'vitest'
import { requirementsSchema } from './requirements.zod'

const valid = {
  project_id: 'p1',
  domain: 'e-commerce' as const,
  users: 100000,
  concurrency: 5000,
  rps: 500,
  peak_rps: 2000,
  data_size: 200,
  read_write_ratio: 0.8,
  latency_sla: 200,
  availability_sla: 99.9,
  budget: 5000,
}

describe('requirementsSchema', () => {
  it('accepts a valid payload', () => {
    expect(requirementsSchema.safeParse(valid).success).toBe(true)
  })
  it('rejects peak_rps below rps', () => {
    expect(requirementsSchema.safeParse({ ...valid, peak_rps: 10 }).success).toBe(false)
  })
  it('rejects concurrency above users', () => {
    expect(requirementsSchema.safeParse({ ...valid, concurrency: 999999 }).success).toBe(false)
  })
})
