import { describe, it, expect } from 'vitest'
import { formatPace, formatDistance, formatDuration, formatElevation, formatHeartrate } from '../format'

describe('format utilities', () => {
  describe('formatDistance', () => {
    it('formats meters to kilometers (metric)', () => {
      expect(formatDistance(1000)).toBe('1.00 km')
      expect(formatDistance(5000)).toBe('5.00 km')
      expect(formatDistance(42195)).toBe('42.20 km')
    })

    it('formats meters to miles (imperial)', () => {
      expect(formatDistance(1609.344, 'imperial')).toBe('1.00 mi')
      expect(formatDistance(8046.72, 'imperial')).toBe('5.00 mi')
    })

    it('handles zero', () => {
      expect(formatDistance(0)).toBe('0.00 km')
    })
  })

  describe('formatDuration', () => {
    it('formats seconds to hours, minutes, seconds', () => {
      expect(formatDuration(3661)).toBe('1h 1m 1s')
      expect(formatDuration(3600)).toBe('1h 0m 0s')
      expect(formatDuration(60)).toBe('1m 0s')
      expect(formatDuration(45)).toBe('45s')
    })

    it('handles zero', () => {
      expect(formatDuration(0)).toBe('0s')
    })
  })

  describe('formatPace', () => {
    it('formats speed in m/s to pace', () => {
      // 3.33 m/s = 5:00 min/km pace
      expect(formatPace(3.333333)).toBe('5:00')
      // 2.5 m/s = 6:40 min/km pace
      expect(formatPace(2.5)).toBe('6:40')
    })

    it('handles zero speed', () => {
      expect(formatPace(0)).toBe('--:--')
    })
  })

  describe('formatElevation', () => {
    it('formats elevation in meters', () => {
      expect(formatElevation(100)).toBe('100 m')
      expect(formatElevation(1234)).toBe('1234 m')
      expect(formatElevation(1234.5)).toBe('1235 m')
    })
  })

  describe('formatHeartrate', () => {
    it('formats heart rate in bpm', () => {
      expect(formatHeartrate(150)).toBe('150 bpm')
      expect(formatHeartrate(150.5)).toBe('151 bpm')
      expect(formatHeartrate(0)).toBe('0 bpm')
    })
  })
})
