import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ActivityFilters from '../ActivityFilters'
import type { ActivityFilters as Filters } from '../../api/activities'

describe('ActivityFilters', () => {
  const defaultFilters: Filters = {}

  it('renders filters button', () => {
    render(<ActivityFilters filters={defaultFilters} onFilterChange={vi.fn()} />)
    expect(screen.getByText('Filters')).toBeInTheDocument()
  })

  it('expands filters when button is clicked', () => {
    render(<ActivityFilters filters={defaultFilters} onFilterChange={vi.fn()} />)

    expect(screen.queryByText('Activity Type')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Filters'))

    expect(screen.getByText('Activity Type')).toBeInTheDocument()
    expect(screen.getByText('Distance Bucket')).toBeInTheDocument()
    expect(screen.getByText('Effort Zone')).toBeInTheDocument()
    expect(screen.getByText('Start Date')).toBeInTheDocument()
    expect(screen.getByText('End Date')).toBeInTheDocument()
  })

  it('shows active filter badge when filters are applied', () => {
    const filters: Filters = { type: 'Run' }
    render(<ActivityFilters filters={filters} onFilterChange={vi.fn()} />)

    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('does not show active badge when no filters are applied', () => {
    render(<ActivityFilters filters={defaultFilters} onFilterChange={vi.fn()} />)
    expect(screen.queryByText('Active')).not.toBeInTheDocument()
  })

  it('shows clear all button when filters are active', () => {
    const filters: Filters = { type: 'Run' }
    render(<ActivityFilters filters={filters} onFilterChange={vi.fn()} />)

    fireEvent.click(screen.getByText('Filters'))
    expect(screen.getByText('Clear all')).toBeInTheDocument()
  })

  it('calls onFilterChange when activity type is changed', () => {
    const onFilterChange = vi.fn()
    render(<ActivityFilters filters={defaultFilters} onFilterChange={onFilterChange} />)

    fireEvent.click(screen.getByText('Filters'))

    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[0], { target: { value: 'Run' } })

    expect(onFilterChange).toHaveBeenCalledWith({ type: 'Run' })
  })

  it('calls onFilterChange when distance bucket is changed', () => {
    const onFilterChange = vi.fn()
    render(<ActivityFilters filters={defaultFilters} onFilterChange={onFilterChange} />)

    fireEvent.click(screen.getByText('Filters'))

    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[1], { target: { value: '10K' } })

    expect(onFilterChange).toHaveBeenCalledWith({ distance_bucket: '10K' })
  })

  it('calls onFilterChange when effort zone is changed', () => {
    const onFilterChange = vi.fn()
    render(<ActivityFilters filters={defaultFilters} onFilterChange={onFilterChange} />)

    fireEvent.click(screen.getByText('Filters'))

    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[2], { target: { value: 'hard' } })

    expect(onFilterChange).toHaveBeenCalledWith({ effort_zone: 'hard' })
  })

  it('calls onFilterChange when start date is changed', () => {
    const onFilterChange = vi.fn()
    render(<ActivityFilters filters={defaultFilters} onFilterChange={onFilterChange} />)

    fireEvent.click(screen.getByText('Filters'))

    const input = screen.getByLabelText('Start Date')
    fireEvent.change(input, { target: { value: '2026-01-01' } })

    expect(onFilterChange).toHaveBeenCalledWith({ start_date: '2026-01-01' })
  })

  it('calls onFilterChange when end date is changed', () => {
    const onFilterChange = vi.fn()
    render(<ActivityFilters filters={defaultFilters} onFilterChange={onFilterChange} />)

    fireEvent.click(screen.getByText('Filters'))

    const input = screen.getByLabelText('End Date')
    fireEvent.change(input, { target: { value: '2026-12-31' } })

    expect(onFilterChange).toHaveBeenCalledWith({ end_date: '2026-12-31' })
  })

  it('clears all filters when clear all is clicked', () => {
    const onFilterChange = vi.fn()
    const filters: Filters = { type: 'Run', distance_bucket: '10K' }
    render(<ActivityFilters filters={filters} onFilterChange={onFilterChange} />)

    fireEvent.click(screen.getByText('Filters'))
    fireEvent.click(screen.getByText('Clear all'))

    expect(onFilterChange).toHaveBeenCalledWith({
      type: undefined,
      distance_bucket: undefined,
      effort_zone: undefined,
      start_date: undefined,
      end_date: undefined,
    })
  })

  it('displays current filter values', () => {
    const filters: Filters = { type: 'Run', distance_bucket: '10K' }
    render(<ActivityFilters filters={filters} onFilterChange={vi.fn()} />)

    fireEvent.click(screen.getByText('Filters'))

    const selects = screen.getAllByRole('combobox')
    expect(selects[0]).toHaveValue('Run')
    expect(selects[1]).toHaveValue('10K')
  })
})
