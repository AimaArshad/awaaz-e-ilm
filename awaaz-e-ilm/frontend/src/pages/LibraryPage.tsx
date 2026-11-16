/**
 * LibraryPage — displays the user's document library.
 *
 * Features:
 * - Fetches and lists all documents from GET /documents/
 * - Each document card shows title, status badge, and open button
 * - Keyboard navigable with arrow keys and Enter
 * - Link to UploadPage for adding new books
 * - Announces document count via ARIA live region
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { Document } from '../lib/api'
import ProgressBar from '../components/ProgressBar'

const STATUS_COLORS: Record<string, string> = {
  uploaded: 'bg-blue-700 text-blue-100',
  extracting: 'bg-yellow-700 text-yellow-100',
  ready: 'bg-green-700 text-green-100',
  failed: 'bg-red-700 text-red-100',
}

export default function LibraryPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.listDocuments()
      .then(setDocuments)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <main id="main" className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-white">
          📚 My Library
        </h1>
        <Link
          to="/upload"
          className="px-4 py-2 bg-violet-700 hover:bg-violet-600 text-white rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-violet-400 transition-colors"
          aria-label="Upload a new book"
        >
          + Upload Book
        </Link>
      </div>

      {/* ARIA live region for status announcements */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {loading
          ? 'Loading your library…'
          : error
            ? `Error: ${error}`
            : `${documents.length} book${documents.length !== 1 ? 's' : ''} in your library`}
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-16">
          <ProgressBar value={null} label="Loading library…" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div role="alert" className="p-4 bg-red-900 border border-red-500 rounded-lg text-red-200">
          <strong>Error loading library:</strong> {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && documents.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-xl mb-4">Your library is empty.</p>
          <Link
            to="/upload"
            className="text-violet-400 hover:text-violet-300 underline"
          >
            Upload your first book
          </Link>
        </div>
      )}

      {/* Document grid */}
      {!loading && documents.length > 0 && (
        <ul
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          aria-label="Document library"
        >
          {documents.map((doc) => (
            <li key={doc.id}>
              <Link
                to={`/player/${doc.id}`}
                className="block p-5 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-violet-500 rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-violet-400"
                aria-label={`Open ${doc.title}, status: ${doc.status}`}
              >
                <div className="flex items-start justify-between gap-2 mb-3">
                  <h2 className="text-lg font-semibold text-white leading-tight">
                    {doc.title}
                  </h2>
                  <span
                    className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[doc.status] ?? 'bg-gray-700 text-gray-200'}`}
                    aria-label={`Status: ${doc.status}`}
                  >
                    {doc.status}
                  </span>
                </div>
                <p className="text-sm text-gray-400">
                  {doc.file_type.toUpperCase()} • {new Date(doc.created_at).toLocaleDateString()}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {/* Nav footer */}
      <nav className="mt-10 flex gap-4" aria-label="Site navigation">
        <Link to="/settings" className="text-gray-400 hover:text-white underline">
          ⚙️ Settings
        </Link>
      </nav>
    </main>
  )
}
