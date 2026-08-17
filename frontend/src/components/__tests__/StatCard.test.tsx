import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatCard from '../StatCard'

describe('StatCard', () => {
  it('renders title and value', () => {
    render(<StatCard title="Total Distance" value="150.5 km" />)
    expect(screen.getByText('Total Distance')).toBeInTheDocument()
    expect(screen.getByText('150.5 km')).toBeInTheDocument()
  })

  it('renders subtitle when provided', () => {
    render(<StatCard title="Activities" value="42" subtitle="This month" />)
    expect(screen.getByText('This month')).toBeInTheDocument()
  })

  it('does not render subtitle when not provided', () => {
    const { container } = render(<StatCard title="Distance" value="100 km" />)
    const paragraphs = container.querySelectorAll('p')
    expect(paragraphs).toHaveLength(2) // title + value only
  })

  it('renders increasing trend', () => {
    render(<StatCard title="Weekly Distance" value="50 km" trend={{ direction: 'increasing', value: '+10%' }} />)
    expect(screen.getByText('+10%')).toBeInTheDocument()
  })

  it('renders decreasing trend', () => {
    render(<StatCard title="Weekly Distance" value="50 km" trend={{ direction: 'decreasing', value: '-5%' }} />)
    expect(screen.getByText('-5%')).toBeInTheDocument()
  })

  it('does not render trend when not provided', () => {
    const { container } = render(<StatCard title="Distance" value="100 km" />)
    const paragraphs = container.querySelectorAll('p')
    expect(paragraphs).toHaveLength(2) // title + value only
  })
})
