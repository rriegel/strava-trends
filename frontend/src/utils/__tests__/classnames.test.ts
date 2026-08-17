import { describe, it, expect } from 'vitest'
import { cn } from '../classnames'

describe('classnames utility', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('handles conditional classes', () => {
    expect(cn('base', true && 'active', false && 'hidden')).toBe('base active')
  })

  it('handles undefined and null', () => {
    expect(cn('base', undefined, null, 'extra')).toBe('base extra')
  })

  it('handles empty input', () => {
    expect(cn()).toBe('')
  })

  it('merges Tailwind classes correctly', () => {
    // twMerge handles conflicting Tailwind classes
    expect(cn('px-4', 'px-6')).toBe('px-6')
    expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500')
  })
})
