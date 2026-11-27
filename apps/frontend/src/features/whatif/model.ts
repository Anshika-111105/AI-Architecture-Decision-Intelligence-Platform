import { BROKERS, CACHES, CLOUDS, DATABASES, type Scenario } from '../../types/proposed'

/** README section 23 example: current 5,000 RPS, 3 replicas, Redis. */
export const BASELINE: Scenario = {
  rps: 5000,
  concurrency: 5000,
  data_size: 200,
  read_write_ratio: 0.8,
  replica_count: 3,
  cpu_limit: 2,
  memory_limit: 4,
  database: 'postgres',
  cache: 'redis',
  messaging: 'kafka',
  cloud: 'aws',
}

/** README section 23 example: what-if 20,000 RPS, 6 replicas, Redis. */
export const README_WHATIF: Scenario = { ...BASELINE, rps: 20000, replica_count: 6 }

type NumericKey = 'rps' | 'concurrency' | 'data_size' | 'read_write_ratio' | 'replica_count' | 'cpu_limit' | 'memory_limit'
type SelectKey = 'database' | 'cache' | 'messaging' | 'cloud'

const n = (v: number) => v.toLocaleString('en-US')

export interface SliderSpec {
  key: NumericKey
  label: string
  min: number
  max: number
  step: number
  format: (v: number) => string
}

export const SLIDERS: SliderSpec[] = [
  { key: 'rps', label: 'Requests per second', min: 100, max: 50000, step: 100, format: n },
  { key: 'concurrency', label: 'Concurrent users', min: 100, max: 100000, step: 100, format: n },
  { key: 'data_size', label: 'Data size (GB)', min: 1, max: 5000, step: 1, format: n },
  { key: 'read_write_ratio', label: 'Read share', min: 0, max: 1, step: 0.05, format: (v) => `${Math.round(v * 100)}% reads` },
  { key: 'replica_count', label: 'Replicas', min: 1, max: 32, step: 1, format: n },
  { key: 'cpu_limit', label: 'vCPU per replica', min: 0.25, max: 16, step: 0.25, format: (v) => String(v) },
  { key: 'memory_limit', label: 'Memory per replica (GB)', min: 0.5, max: 64, step: 0.5, format: (v) => String(v) },
]

export interface SelectSpec {
  key: SelectKey
  label: string
  options: readonly string[]
}

export const SELECTS: SelectSpec[] = [
  { key: 'database', label: 'Database', options: DATABASES },
  { key: 'cache', label: 'Cache', options: CACHES },
  { key: 'messaging', label: 'Messaging', options: BROKERS },
  { key: 'cloud', label: 'Cloud', options: CLOUDS },
]

export interface FieldChange {
  key: keyof Scenario
  label: string
  from: string
  to: string
}

/** Which settings differ between two scenarios, in display form. */
export function changedFields(a: Scenario, b: Scenario): FieldChange[] {
  const changes: FieldChange[] = []
  for (const s of SLIDERS) {
    if (a[s.key] !== b[s.key]) changes.push({ key: s.key, label: s.label, from: s.format(a[s.key]), to: s.format(b[s.key]) })
  }
  for (const s of SELECTS) {
    if (a[s.key] !== b[s.key]) changes.push({ key: s.key, label: s.label, from: a[s.key], to: b[s.key] })
  }
  return changes
}
