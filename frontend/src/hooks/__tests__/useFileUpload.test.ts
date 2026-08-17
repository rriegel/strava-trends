import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useFileUpload } from '../useFileUpload'
import { uploadApi } from '../../api/uploads'

vi.mock('../../api/uploads', () => ({
  uploadApi: {
    uploadFile: vi.fn(),
    uploadBatch: vi.fn(),
  },
}))

describe('useFileUpload', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('has correct initial state', () => {
    const { result } = renderHook(() => useFileUpload())

    expect(result.current.isUploading).toBe(false)
    expect(result.current.progress).toBe(0)
    expect(result.current.results).toEqual([])
    expect(result.current.error).toBeNull()
  })

  it('uploads a single file successfully', async () => {
    const mockResult = {
      filename: 'test.fit',
      status: 'success' as const,
      message: 'Activity imported successfully',
      activity_id: 1,
    }
    vi.mocked(uploadApi.uploadFile).mockResolvedValue(mockResult)

    const { result } = renderHook(() => useFileUpload())
    const file = new File(['content'], 'test.fit', { type: 'application/octet-stream' })

    await act(async () => {
      await result.current.uploadFiles([file])
    })

    expect(uploadApi.uploadFile).toHaveBeenCalledWith(file)
    expect(uploadApi.uploadBatch).not.toHaveBeenCalled()
    expect(result.current.isUploading).toBe(false)
    expect(result.current.results).toHaveLength(1)
    expect(result.current.results[0].status).toBe('success')
  })

  it('uploads multiple files as batch', async () => {
    const mockBatchResponse = {
      total_files: 2,
      success_count: 1,
      duplicate_count: 1,
      error_count: 0,
      results: [
        { filename: 'a.fit', status: 'success' as const, message: 'OK' },
        { filename: 'b.fit', status: 'duplicate' as const, message: 'Already imported' },
      ],
    }
    vi.mocked(uploadApi.uploadBatch).mockResolvedValue(mockBatchResponse)

    const { result } = renderHook(() => useFileUpload())
    const files = [
      new File(['a'], 'a.fit', { type: 'application/octet-stream' }),
      new File(['b'], 'b.fit', { type: 'application/octet-stream' }),
    ]

    await act(async () => {
      await result.current.uploadFiles(files)
    })

    expect(uploadApi.uploadBatch).toHaveBeenCalledWith(files)
    expect(uploadApi.uploadFile).not.toHaveBeenCalled()
    expect(result.current.results).toHaveLength(2)
    expect(result.current.results[0].status).toBe('success')
    expect(result.current.results[1].status).toBe('duplicate')
  })

  it('handles upload error', async () => {
    vi.mocked(uploadApi.uploadFile).mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useFileUpload())
    const file = new File(['content'], 'test.fit', { type: 'application/octet-stream' })

    await act(async () => {
      try {
        await result.current.uploadFiles([file])
      } catch {
        // Expected
      }
    })

    expect(result.current.isUploading).toBe(false)
    expect(result.current.error).toBe('Network error')
    expect(result.current.results).toHaveLength(0)
  })

  it('does nothing when called with empty files array', async () => {
    const { result } = renderHook(() => useFileUpload())

    await act(async () => {
      await result.current.uploadFiles([])
    })

    expect(uploadApi.uploadFile).not.toHaveBeenCalled()
    expect(uploadApi.uploadBatch).not.toHaveBeenCalled()
  })

  it('reset clears state', async () => {
    vi.mocked(uploadApi.uploadFile).mockResolvedValue({
      filename: 'test.fit',
      status: 'success',
      message: 'OK',
    })

    const { result } = renderHook(() => useFileUpload())
    const file = new File(['content'], 'test.fit', { type: 'application/octet-stream' })

    await act(async () => {
      await result.current.uploadFiles([file])
    })

    expect(result.current.results).toHaveLength(1)

    act(() => {
      result.current.reset()
    })

    expect(result.current.results).toHaveLength(0)
    expect(result.current.error).toBeNull()
    expect(result.current.isUploading).toBe(false)
  })
})
