import { describe, it, expect } from 'vitest'
import { formatPace, formatPaceDecimal, isPaceDisplay, formatDistance, formatDuration, formatElevation, formatHeartrate, distanceUnitLabel, elevationUnitLabel } from '../format'

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

  describe('formatPace (speed m/s -> M:SS min/km)', () => {
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

  describe('formatPaceDecimal (decimal min/km -> M:SS)', () => {
    it('formats decimal minutes as M:SS', () => {
      expect(formatPaceDecimal(5.0)).toBe('5:00')
      expect(formatPaceDecimal(5.5)).toBe('5:30')
      expect(formatPaceDecimal(6.6666666)).toBe('6:40')
      expect(formatPaceDecimal(4.25)).toBe('4:15')
    })

    it('carries seconds >= 60 into the next minute', () => {
      // 4.999 * 60 = 299.94 -> rounds to 300s = 5:00, not 4:60
      expect(formatPaceDecimal(4.999)).toBe('5:00')
    })

    it('handles zero and negative as no data', () => {
      expect(formatPaceDecimal(0)).toBe('--:--')
      expect(formatPaceDecimal(-1)).toBe('--:--')
    })
  })

  describe('isPaceDisplay', () => {
    it('flags speed and GAP as pace-formatted metrics', () => {
      expect(isPaceDisplay('average_speed')).toBe(true)
      expect(isPaceDisplay('grade_adjusted_pace')).toBe(true)
    })

    it('does not flag non-pace metrics', () => {
      expect(isPaceDisplay('average_heartrate')).toBe(false)
      expect(isPaceDisplay('average_cadence')).toBe(false)
      expect(isPaceDisplay('distance')).toBe(false)
      expect(isPaceDisplay('total_elevation_gain')).toBe(false)
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

  describe('unit system (metric/imperial)', () => {
    describe('formatPace with unit', () => {
      it('converts m/s to min/mi in imperial', () => {
        // 3.333333 m/s = 5:00 min/km = 8:02.7 min/mi (5:00 * 1.609344 = 8:04.7 in seconds:
        // 300 s/km * 1.609344 = 482.8 s/mi = 8:02.8)
        const imperial = formatPace(3.333333, 'imperial')
        const secondsPerMi = (1000 / 3.333333) * 1.609344
        const mins = Math.floor(secondsPerMi / 60)
        const secs = Math.round(secondsPerMi % 60)
        expect(imperial).toBe(`${mins}:${String(secs).padStart(2, '0')}`)
      })

      it('metric default unchanged', () => {
        expect(formatPace(3.333333, 'metric')).toBe('5:00')
        expect(formatPace(2.5, 'metric')).toBe('6:40')
      })

      it('handles zero speed in both systems', () => {
        expect(formatPace(0, 'imperial')).toBe('--:--')
        expect(formatPace(0, 'metric')).toBe('--:--')
      })
    })

    describe('formatElevation with unit', () => {
      it('converts meters to feet (imperial)', () => {
        expect(formatElevation(100, 'imperial')).toBe('328 ft')
        expect(formatElevation(0, 'imperial')).toBe('0 ft')
      })

      it('metric default unchanged', () => {
        expect(formatElevation(100, 'metric')).toBe('100 m')
        expect(formatElevation(1234.5, 'metric')).toBe('1235 m')
      })
    })

    describe('formatDistance with unit', () => {
      it('2 decimals in both systems (Ryan decision)', () => {
        expect(formatDistance(8046.72, 'imperial')).toBe('5.00 mi')
        expect(formatDistance(42195, 'imperial')).toBe('26.22 mi')
        expect(formatDistance(42195, 'metric')).toBe('42.20 km')
      })
    })

    describe('unit labels', () => {
      it('distance label: km vs mi', () => {
        expect(distanceUnitLabel('metric')).toBe('km')
        expect(distanceUnitLabel('imperial')).toBe('mi')
      })

      it('elevation label: m vs ft', () => {
        expect(elevationUnitLabel('metric')).toBe('m')
        expect(elevationUnitLabel('imperial')).toBe('ft')
      })
    })
  })
})
