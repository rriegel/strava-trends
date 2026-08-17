import apiClient from './client'

export interface UploadResult {
  filename: string
  status: 'success' | 'duplicate' | 'error'
  message: string
  activity_id?: number
  activity_name?: string
  activity_type?: string
  start_date?: string
}

export interface BatchUploadResponse {
  total_files: number
  success_count: number
  duplicate_count: number
  error_count: number
  results: UploadResult[]
}

export interface SupportedFormats {
  formats: string[]
  max_file_size_mb: number
  description: Record<string, string>
}

export const uploadApi = {
  async uploadFile(file: File): Promise<UploadResult> {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await apiClient.post<UploadResult>('/uploads/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    
    return response.data
  },

  async uploadBatch(files: File[]): Promise<BatchUploadResponse> {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })
    
    const response = await apiClient.post<BatchUploadResponse>('/uploads/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    
    return response.data
  },

  async getSupportedFormats(): Promise<SupportedFormats> {
    const response = await apiClient.get<SupportedFormats>('/uploads/supported-formats')
    return response.data
  },
}
