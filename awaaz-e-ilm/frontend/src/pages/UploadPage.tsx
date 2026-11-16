/**
 * UploadPage — drag-and-drop / file-input document upload.
 *
 * Features:
 * - Drag and drop target with visual feedback
 * - File input with accessible label and ARIA description
 * - Shows upload progress (simulated via fetch with ReadableStream in Milestone 2)
 * - Navigates to PlayerPage on successful upload
 * - Keyboard accessible (Enter/Space on drop zone)
 */
import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import ProgressBar from '../components/ProgressBar'

const ACCEPTED_TYPES = [
  'application/pdf',
  'application/epub+zip',
  'text/plain',
  'image/png',
  'image/jpeg',
]
const ACCEPTED_EXT = '.pdf,.epub,.txt,.png,.jpg,.jpeg'

export default function UploadPage() {
  const navigate = useNavigate()
  const [isDragging, setIsDragging] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = (f: File) => {
    if (!ACCEPTED_TYPES.includes(f.type) && !f.name.match(/\.(pdf|epub|txt|png|jpe?g)$/i)) {
      setError(`Unsupported file type: ${f.type || f.name}. Accepted: PDF, EPUB, TXT, PNG, JPEG.`)
      return
    }
    setFile(f)
    setTitle(f.name.replace(/\.[^.]+$/, ''))
    setError(null)
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) handleFile(dropped)
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const doc = await api.uploadDocument(file, title || file.name)
      navigate(`/player/${doc.id}`)
    } catch (e) {
      setError((e as Error).message)
      setUploading(false)
    }
  }

  return (
    <main id="main" className="max-w-2xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold text-white mb-8">📤 Upload a Book</h1>

      {/* Error */}
      {error && (
        <div role="alert" className="mb-4 p-4 bg-red-900 border border-red-500 rounded-lg text-red-200">
          {error}
        </div>
      )}

      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Drop zone: drag and drop a PDF, EPUB, or image file here, or press Enter to browse"
        aria-describedby="upload-hint"
        className={`relative flex flex-col items-center justify-center p-10 border-2 border-dashed rounded-2xl transition-colors cursor-pointer
          ${isDragging ? 'border-violet-400 bg-violet-900/20' : 'border-gray-600 hover:border-gray-400 bg-gray-800/50'}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            document.getElementById('file-input')?.click()
          }
        }}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <span className="text-5xl mb-4" aria-hidden="true">📁</span>
        <p className="text-white font-medium text-lg">
          {file ? file.name : 'Drag & drop your book here'}
        </p>
        <p id="upload-hint" className="text-gray-400 text-sm mt-1">
          or click to browse — PDF, EPUB, TXT, PNG, JPEG
        </p>

        {/* Hidden file input */}
        <input
          id="file-input"
          type="file"
          accept={ACCEPTED_EXT}
          className="sr-only"
          aria-label="Choose a file to upload"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) handleFile(f)
          }}
        />
      </div>

      {/* Title field */}
      {file && (
        <div className="mt-6">
          <label htmlFor="book-title" className="block text-sm font-medium text-gray-300 mb-1">
            Book Title
          </label>
          <input
            id="book-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-400"
            placeholder="Enter book title…"
          />
        </div>
      )}

      {/* Upload button */}
      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="mt-6 w-full px-6 py-3 bg-violet-700 hover:bg-violet-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-violet-400"
        aria-busy={uploading}
        aria-disabled={!file || uploading}
      >
        {uploading ? 'Uploading…' : 'Upload Book'}
      </button>

      {uploading && <ProgressBar value={null} label="Uploading…" className="mt-4" />}

      <p className="mt-6 text-center">
        <a href="/" className="text-gray-400 hover:text-white underline">← Back to Library</a>
      </p>
    </main>
  )
}
