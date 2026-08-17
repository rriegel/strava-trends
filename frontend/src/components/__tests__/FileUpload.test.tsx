import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FileUpload from '../FileUpload'
import { useFileUpload } from '../../hooks/useFileUpload'

vi.mock('../../hooks/useFileUpload', () => ({
  useFileUpload: vi.fn(),
}))

const mockUseFileUpload = vi.mocked(useFileUpload)

describe('FileUpload', () => {
  const defaultMockState = {
    isUploading: false,
    progress: 0,
    results: [],
    error: null,
    uploadFiles: vi.fn(),
    reset: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseFileUpload.mockReturnValue({ ...defaultMockState })
  })

  it('renders the drop zone', () => {
    render(<FileUpload />)
    expect(screen.getByText(/Click to upload/i)).toBeInTheDocument()
    expect(screen.getByText(/FIT, GPX, or TCX files/i)).toBeInTheDocument()
  })

  it('does not show selected files section initially', () => {
    render(<FileUpload />)
    expect(screen.queryByText(/file.* selected/i)).not.toBeInTheDocument()
  })

  it('shows selected files after file input change', async () => {
    const user = userEvent.setup()
    render(<FileUpload />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['content'], 'activity.fit', { type: 'application/octet-stream' })

    await user.upload(input, file)

    expect(screen.getByText('1 file selected')).toBeInTheDocument()
    expect(screen.getByText('activity.fit')).toBeInTheDocument()
  })

  it('filters out unsupported file formats', async () => {
    const user = userEvent.setup()
    render(<FileUpload />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const validFile = new File(['content'], 'run.fit', { type: 'application/octet-stream' })
    const invalidFile = new File(['content'], 'doc.pdf', { type: 'application/pdf' })

    await user.upload(input, [validFile, invalidFile])

    expect(screen.getByText('run.fit')).toBeInTheDocument()
    expect(screen.queryByText('doc.pdf')).not.toBeInTheDocument()
  })

  it('shows upload button when files are selected', async () => {
    const user = userEvent.setup()
    render(<FileUpload />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['content'], 'activity.gpx', { type: 'application/octet-stream' })

    await user.upload(input, file)

    expect(screen.getByRole('button', { name: /Upload 1 file/i })).toBeInTheDocument()
  })

  it('calls uploadFiles when upload button is clicked', async () => {
    const user = userEvent.setup()
    const uploadFiles = vi.fn()
    mockUseFileUpload.mockReturnValue({ ...defaultMockState, uploadFiles })

    render(<FileUpload />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['content'], 'activity.fit', { type: 'application/octet-stream' })

    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: /Upload 1 file/i }))

    expect(uploadFiles).toHaveBeenCalledWith([file])
  })

  it('disables upload button while uploading', async () => {
    const user = userEvent.setup()
    mockUseFileUpload.mockReturnValue({ ...defaultMockState, isUploading: true })

    render(<FileUpload />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['content'], 'activity.fit', { type: 'application/octet-stream' })

    await user.upload(input, file)

    const button = screen.getByRole('button', { name: /Uploading/i })
    expect(button).toBeDisabled()
  })

  it('shows error message when error is present', () => {
    mockUseFileUpload.mockReturnValue({
      ...defaultMockState,
      error: 'Network error',
    })

    render(<FileUpload />)

    expect(screen.getByText('Upload failed')).toBeInTheDocument()
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('shows upload results', () => {
    mockUseFileUpload.mockReturnValue({
      ...defaultMockState,
      results: [
        { filename: 'run.fit', status: 'success', message: 'Imported' },
        { filename: 'old.fit', status: 'duplicate', message: 'Already imported' },
      ],
    })

    render(<FileUpload />)

    expect(screen.getByText('Upload Results')).toBeInTheDocument()
    expect(screen.getByText('run.fit')).toBeInTheDocument()
    expect(screen.getByText('old.fit')).toBeInTheDocument()
    expect(screen.getByText('Imported')).toBeInTheDocument()
    expect(screen.getByText('Already imported')).toBeInTheDocument()
  })

  it('calls onUploadComplete callback after successful upload', async () => {
    const user = userEvent.setup()
    const onUploadComplete = vi.fn()
    const uploadFiles = vi.fn().mockResolvedValue({})
    mockUseFileUpload.mockReturnValue({ ...defaultMockState, uploadFiles })

    render(<FileUpload onUploadComplete={onUploadComplete} />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['content'], 'activity.fit', { type: 'application/octet-stream' })

    await user.upload(input, file)
    await user.click(screen.getByRole('button', { name: /Upload 1 file/i }))

    await waitFor(() => {
      expect(onUploadComplete).toHaveBeenCalled()
    })
  })
})
