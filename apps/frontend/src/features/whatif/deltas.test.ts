import { describe, expect, it } from 'vitest'
import { mockWhatIfPredictions } from '../../mocks/whatifModel'
import { deltaOf } from './deltas'
import { BASELINE, changedFields, README_WHATIF } from './model'

describe('deltaOf', () => {
  it('lower-is-better: an increase is worse', () => {
    expect(deltaOf(100, 150, 'lower')).toEqual({ abs: 50, pct: 50, verdict: 'worse' })
  })
  it('higher-is-better: an increase is better', () => {
    expect(deltaOf(1000, 800, 'higher')).toEqual({ abs: -200, pct: -20, verdict: 'worse' })
    expect(deltaOf(1000, 1500, 'higher').verdict).toBe('better')
  })
  it('reports no change and handles a zero baseline', () => {
    expect(deltaOf(5, 5, 'lower').verdict).toBe('same')
    expect(deltaOf(0, 10, 'lower').pct).toBeNull()
  })
})

describe('changedFields', () => {
  it('lists the README example change (RPS and replicas only)', () => {
    expect(changedFields(BASELINE, README_WHATIF)).toEqual([
      { key: 'rps', label: 'Requests per second', from: '5,000', to: '20,000' },
      { key: 'replica_count', label: 'Replicas', from: '3', to: '6' },
    ])
  })
  it('lists changed dropdown settings by value', () => {
    expect(changedFields(BASELINE, { ...BASELINE, cache: 'none' })).toEqual([{ key: 'cache', label: 'Cache', from: 'redis', to: 'none' }])
  })
})

describe('mock what-if model behaves sensibly', () => {
  const at = (patch: Partial<typeof BASELINE>) => mockWhatIfPredictions({ ...BASELINE, ...patch })

  it('more load means higher latency and CPU', () => {
    expect(at({ rps: 20000 }).latency.p95_ms).toBeGreaterThan(at({}).latency.p95_ms)
    expect(at({ rps: 20000 }).resources.cpu_utilization_pct).toBeGreaterThan(at({}).resources.cpu_utilization_pct)
  })
  it('more replicas means lower latency but higher cost', () => {
    expect(at({ replica_count: 6 }).latency.p95_ms).toBeLessThan(at({}).latency.p95_ms)
    expect(at({ replica_count: 6 }).cost.estimated_monthly_usd).toBeGreaterThan(at({}).cost.estimated_monthly_usd)
  })
  it('a cache lowers latency for read-heavy traffic', () => {
    expect(at({ cache: 'redis' }).latency.p95_ms).toBeLessThan(at({ cache: 'none' }).latency.p95_ms)
  })
  it('throughput never exceeds the offered load, and percentiles stay ordered', () => {
    const p = at({ rps: 50000, replica_count: 1 })
    expect(p.throughput.predicted_rps).toBeLessThanOrEqual(50000)
    expect(p.latency.p50_ms).toBeLessThan(p.latency.p90_ms)
    expect(p.latency.p90_ms).toBeLessThan(p.latency.p95_ms)
    expect(p.latency.p95_ms).toBeLessThan(p.latency.p99_ms)
    expect(p.resources.cpu_utilization_pct).toBe(100)
  })
})
