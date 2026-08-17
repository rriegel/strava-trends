import { useState } from 'react'
import FileUpload from '../components/FileUpload'

export default function Activities() {
  const [showUpload, setShowUpload] = useState(false)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Activities</h1>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {showUpload ? 'Hide Upload' : 'Upload Files'}
        </button>
      </div>

      {showUpload && (
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Import Activities</h2>
          <FileUpload onUploadComplete={() => {
            // Refresh activities list here when implemented
            console.log('Upload complete, refresh activities')
          }} />
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border p-6">
        <p className="text-gray-500">Activity list will appear here.</p>
      </div>
    </div>
  )
}
