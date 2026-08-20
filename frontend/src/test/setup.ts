import '@testing-library/jest-dom'

// Polyfill ResizeObserver for Recharts in jsdom
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = ResizeObserverMock as any
