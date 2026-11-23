import '@testing-library/jest-dom/vitest'

// jsdom has no layout engine. Recharts' ResponsiveContainer needs ResizeObserver, so
// provide a do-nothing version for every test (a test can still replace it).
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
}
