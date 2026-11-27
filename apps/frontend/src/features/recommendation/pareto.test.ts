import { describe, expect, it } from 'vitest'
import { paretoFront } from './pareto'

describe('paretoFront (cost and latency, both lower-is-better)', () => {
  it('keeps every option when each one wins on something', () => {
    const f = paretoFront(
      [
        { id: 'cheap', x: 1800, y: 160 },
        { id: 'middle', x: 2600, y: 135 },
        { id: 'fast', x: 5400, y: 115 },
      ],
      'lower',
      'lower',
    )
    expect([...f].sort()).toEqual(['cheap', 'fast', 'middle'])
  })

  it('drops an option that another beats on both objectives', () => {
    const f = paretoFront(
      [
        { id: 'middle', x: 2600, y: 135 },
        { id: 'worse', x: 3000, y: 170 },
      ],
      'lower',
      'lower',
    )
    expect([...f]).toEqual(['middle'])
  })

  it('respects higher-is-better on an axis', () => {
    // x: cost (lower), y: scalability (higher)
    const f = paretoFront(
      [
        { id: 'a', x: 100, y: 5 },
        { id: 'b', x: 100, y: 9 }, // same cost, more scalable: beats a
      ],
      'lower',
      'higher',
    )
    expect([...f]).toEqual(['b'])
  })

  it('keeps identical points', () => {
    const f = paretoFront([{ id: 'a', x: 1, y: 1 }, { id: 'b', x: 1, y: 1 }], 'lower', 'lower')
    expect(f.size).toBe(2)
  })
})
