import { useEffect, useState } from 'react'

/**
 * Returns `value` only after it has stopped changing for `delayMs`. Used for sliders:
 * the slider moves instantly, but we call the API once the user pauses instead of on
 * every pixel of movement.
 */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])
  return debounced
}
