import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { uploadApi, type UploadResult, type BatchUploadResponse } from '../api/uploads'
import { ACTIVITY_DATA_INVALIDATED_KEYS } from '../api/queryKeys'

export interface FileUploadState {
  isUploading: boolean
  progress: number
  results: UploadResult[]
  error: string | null
}


export function useFileUpload() {
  const [state, setState] = useState<FileUploadState>({
    isUploading: false,
    progress: 0,
    results: [],
    error: null,
  })
  const queryClient = useQueryClient()

  const uploadFiles = useCallback(async (files: File[]) => {
    if (files.length === 0) return

    setState({
      isUploading: true,
      progress: 0,
      results: [],
      error: null,
    })

    try {
      let response: BatchUploadResponse

      if (files.length === 1) {
        // Single file upload
        const result = await uploadApi.uploadFile(files[0])
        response = {
          total_files: 1,
          success_count: result.status === 'success' ? 1 : 0,
          duplicate_count: result.status === 'duplicate' ? 1 : 0,
          error_count: result.status === 'error' ? 1 : 0,
          results: [result],
        }
      } else {
        // Batch upload
        response = await uploadApi.uploadBatch(files)
      }

      setState({
        isUploading: false,
        progress: 100,
        results: response.results,
        error: null,
      })

      // Mark every activity-derived query stale so pages show fresh data on
      // next visit. Invalidate (not just stale): mounted queries refetch
      // immediately, and this also covers the wipe-and-reupload case where
      // a page's cached copy predates the new data entirely.
      for (const key of ACTIVITY_DATA_INVALIDATED_KEYS) {
        queryClient.invalidateQueries({ queryKey: [key] })
      }

      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed'
      setState({
        isUploading: false,
        progress: 0,
        results: [],
        error: errorMessage,
      })
      throw err
    }
  }, [queryClient])

  const reset = useCallback(() => {
    setState({
      isUploading: false,
      progress: 0,
      results: [],
      error: null,
    })
  }, [])

  return {
    ...state,
    uploadFiles,
    reset,
  }
}
