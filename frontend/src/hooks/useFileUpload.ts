import { useState, useCallback } from 'react'
import { uploadApi, type UploadResult, type BatchUploadResponse } from '../api/uploads'

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
  }, [])

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
