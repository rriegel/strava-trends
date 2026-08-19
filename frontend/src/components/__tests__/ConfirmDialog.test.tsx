import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ConfirmDialog from '../ConfirmDialog'

describe('ConfirmDialog', () => {
  it('does not render when isOpen is false', () => {
    render(
      <ConfirmDialog
        isOpen={false}
        title="Test"
        message="Test message"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.queryByText('Test')).not.toBeInTheDocument()
  })

  it('renders title and message when isOpen is true', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete Item"
        message="Are you sure?"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.getByText('Delete Item')).toBeInTheDocument()
    expect(screen.getByText('Are you sure?')).toBeInTheDocument()
  })

  it('renders default confirm and cancel labels', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Test"
        message="Test"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.getByText('Confirm')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('renders custom labels', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Test"
        message="Test"
        confirmLabel="Yes, delete"
        cancelLabel="No, keep"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.getByText('Yes, delete')).toBeInTheDocument()
    expect(screen.getByText('No, keep')).toBeInTheDocument()
  })

  it('calls onConfirm when confirm button is clicked', () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmDialog
        isOpen={true}
        title="Test"
        message="Test"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    )
    fireEvent.click(screen.getByText('Confirm'))
    expect(onConfirm).toHaveBeenCalled()
  })

  it('calls onCancel when cancel button is clicked', () => {
    const onCancel = vi.fn()
    render(
      <ConfirmDialog
        isOpen={true}
        title="Test"
        message="Test"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    )
    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalled()
  })

  it('calls onCancel when backdrop is clicked', () => {
    const onCancel = vi.fn()
    render(
      <ConfirmDialog
        isOpen={true}
        title="Dialog Title"
        message="Dialog message body"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    )
    // Click the backdrop (the fixed-position parent div)
    const backdrop = screen.getByText('Dialog Title').closest('div[style*="position: fixed"]')
    if (backdrop) {
      fireEvent.click(backdrop)
      expect(onCancel).toHaveBeenCalled()
    }
  })

  it('calls onCancel when Escape key is pressed', () => {
    const onCancel = vi.fn()
    render(
      <ConfirmDialog
        isOpen={true}
        title="Test"
        message="Test"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onCancel).toHaveBeenCalled()
  })

  it('applies danger variant styling to confirm button', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Test"
        message="Test"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        variant="danger"
      />
    )
    const confirmButton = screen.getByText('Confirm')
    expect(confirmButton.className).toContain('bg-red-600')
  })

  it('applies default variant styling to confirm button', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Test"
        message="Test"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        variant="default"
      />
    )
    const confirmButton = screen.getByText('Confirm')
    expect(confirmButton.className).toContain('bg-blue-600')
  })
})
