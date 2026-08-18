import { useState, useRef, type DragEvent, type ChangeEvent } from 'react'
import { useFileUpload } from '../hooks/useFileUpload'
import { useToast } from './ToastProvider'
import { cn } from '../utils/classnames'

const ACCEPTED_FORMATS = ['.fit', '.gpx', '.tcx']
const MAX_FILE_SIZE_MB = 50

interface FileUploadProps {
  onUploadComplete?: () => void
}

export default function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { isUploading, results, error, uploadFiles, reset } = useFileUpload()
  const { addToast } = useToast()

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const validFiles = validateFiles(files)
    setSelectedFiles(validFiles)
  }

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files)
      const validFiles = validateFiles(files)
      setSelectedFiles(validFiles)
    }
  }

  const validateFiles = (files: File[]): File[] => {
    return files.filter((file) => {
      const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
      const isValidFormat = ACCEPTED_FORMATS.includes(ext)
      const isValidSize = file.size <= MAX_FILE_SIZE_MB * 1024 * 1024

      if (!isValidFormat) {
        console.warn(`Skipping ${file.name}: unsupported format`)
      }
      if (!isValidSize) {
        console.warn(`Skipping ${file.name}: file too large (max ${MAX_FILE_SIZE_MB}MB)`)
      }

      return isValidFormat && isValidSize
    })
  }

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return

    try {
      const response = await uploadFiles(selectedFiles)
      
      if (response) {
        const { success_count, duplicate_count, error_count } = response
        
        // Show appropriate toast based on results
        if (success_count > 0 && duplicate_count === 0 && error_count === 0) {
          addToast('success', `Successfully uploaded ${success_count} activit${success_count === 1 ? 'y' : 'ies'}`)
        } else if (duplicate_count > 0 && success_count === 0 && error_count === 0) {
          addToast('warning', `${duplicate_count} activit${duplicate_count === 1 ? 'y was' : 'ies were'} already imported`)
        } else if (error_count > 0 && success_count === 0 && duplicate_count === 0) {
          addToast('error', `Failed to upload ${error_count} file${error_count === 1 ? '' : 's'}`)
        } else {
          // Mixed results
          const parts = []
          if (success_count > 0) parts.push(`${success_count} succeeded`)
          if (duplicate_count > 0) parts.push(`${duplicate_count} duplicates`)
          if (error_count > 0) parts.push(`${error_count} failed`)
          addToast('info', `Upload complete: ${parts.join(', ')}`)
        }
      }
      
      onUploadComplete?.()
    } catch (err) {
      console.error('Upload failed:', err)
      addToast('error', 'Upload failed. Please try again.')
    }
  }

  const handleClear = () => {
    setSelectedFiles([])
    reset()
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400 bg-white'
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".fit,.gpx,.tcx"
          onChange={handleFileSelect}
          className="hidden"
        />

        <div className="space-y-2">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
            aria-hidden="true"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          <div className="text-sm text-gray-600">
            <span className="font-medium text-blue-600">Click to upload</span> or drag and drop
          </div>
          <div className="text-xs text-gray-500">
            FIT, GPX, or TCX files (max {MAX_FILE_SIZE_MB}MB each)
          </div>
        </div>
      </div>

      {/* Selected Files */}
      {selectedFiles.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
            </h3>
            <button
              onClick={handleClear}
              disabled={isUploading}
              className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50"
            >
              Clear all
            </button>
          </div>

          <div className="space-y-2 max-h-48 overflow-y-auto">
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between bg-white rounded px-3 py-2 text-sm"
              >
                <div className="flex items-center space-x-2 min-w-0 flex-1">
                  <svg
                    className="h-4 w-4 text-gray-400 flex-shrink-0"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  <span className="truncate text-gray-900">{file.name}</span>
                </div>
                <span className="text-gray-500 flex-shrink-0 ml-2">
                  {formatFileSize(file.size)}
                </span>
              </div>
            ))}
          </div>

          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="mt-4 w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isUploading ? 'Uploading...' : `Upload ${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''}`}
          </button>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-red-400 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Upload failed</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-3">Upload Results</h3>
          <div className="space-y-2">
            {results.map((result, index) => (
              <div
                key={index}
                className={cn(
                  'flex items-start space-x-2 text-sm rounded px-3 py-2',
                  result.status === 'success' && 'bg-green-50 text-green-800',
                  result.status === 'duplicate' && 'bg-yellow-50 text-yellow-800',
                  result.status === 'error' && 'bg-red-50 text-red-800'
                )}
              >
                <svg
                  className="h-4 w-4 flex-shrink-0 mt-0.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  {result.status === 'success' && (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  )}
                  {result.status === 'duplicate' && (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  )}
                  {result.status === 'error' && (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  )}
                </svg>
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{result.filename}</div>
                  <div className="text-xs opacity-75">{result.message}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
