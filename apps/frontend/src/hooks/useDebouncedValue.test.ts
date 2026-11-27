import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDebouncedValue } from './useDebouncedValue'

describe('useDebouncedValue', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('keeps the old value until the input has been still for the delay', () => {
    const { result, rerender } = renderHook(({ v }) => useDebouncedValue(v, 300), { initialProps: { v: 1 } })
    expect(result.current).toBe(1)
    rerender({ v: 2 })
    act(() => vi.advanceTimersByTime(299))
    expect(result.current).toBe(1)
    act(() => vi.advanceTimersByTime(1))
    expect(result.current).toBe(2)
  })

  it('restarts the wait when the value changes again, so only the last value is used', () => {
    const { result, rerender } = renderHook(({ v }) => useDebouncedValue(v, 300), { initialProps: { v: 1 } })
    rerender({ v: 2 })
    act(() => vi.advanceTimersByTime(200))
    rerender({ v: 3 })
    act(() => vi.advanceTimersByTime(200))
    expect(result.current).toBe(1) // 2 never became the debounced value
    act(() => vi.advanceTimersByTime(100))
    expect(result.current).toBe(3)
  })
})
