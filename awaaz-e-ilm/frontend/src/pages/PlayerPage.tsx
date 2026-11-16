/**
 * PlayerPage — main audiobook player interface.
 *
 * Layout:
 * - Left panel: chapter list with status indicators
 * - Main area: audio player controls + transcript
 * - Right panel: voice command button
 *
 * Keyboard shortcuts (from useKeyboardShortcuts):
 *   K         → play/pause
 *   J         → back 30 s
 *   L         → forward 30 s
 *   N         → next chapter
 *   P         → previous chapter
 *   Space     → push-to-talk (hold)
 *
 * Voice: push-to-talk sends audio to /ws/voice and applies returned intent.
 */
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { Document, Chapter } from '../lib/api'
import AudioPlayer from '../components/AudioPlayer'
import ChapterList from '../components/ChapterList'
import VoiceButton from '../components/VoiceButton'
import ProgressBar from '../components/ProgressBar'

export default function PlayerPage() {
  const { documentId } = useParams<{ documentId: string }>()
  const docId = Number(documentId)

  const [document_, setDocument] = useState<Document | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [currentChapter, setCurrentChapter] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')

  useEffect(() => {
    if (!docId) return
    Promise.all([
      api.getDocument(docId),
      api.listChapters(docId),
    ])
      .then(([doc, chs]) => {
        setDocument(doc)
        setChapters(chs)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [docId])

  const handleChapterSelect = (index: number) => {
    setCurrentChapter(index)
    setAnnouncement(`Switched to chapter ${index + 1}: ${chapters[index]?.title ?? ''}`)
  }

  const handleVoiceResult = (result: { intent: string; params: Record<string, unknown> }) => {
    switch (result.intent) {
      case 'navigate_chapter': {
        const ch = (result.params.chapter as number) - 1
        if (ch >= 0 && ch < chapters.length) handleChapterSelect(ch)
        break
      }
      case 'pause':
        setAnnouncement('Paused')
        break
      case 'play':
        setAnnouncement('Playing')
        break
      default:
        setAnnouncement(`Command: ${result.intent}`)
    }
  }

  if (loading) return (
    <main id="main" className="max-w-5xl mx-auto px-4 py-10">
      <ProgressBar value={null} label="Loading player…" />
    </main>
  )

  if (error) return (
    <main id="main" className="max-w-5xl mx-auto px-4 py-10">
      <div role="alert" className="p-4 bg-red-900 border border-red-500 rounded-lg text-red-200">
        {error}
      </div>
    </main>
  )

  return (
    <main id="main" className="max-w-6xl mx-auto px-4 py-6">
      {/* ARIA live announcement region */}
      <div aria-live="assertive" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link to="/" className="text-gray-400 hover:text-white" aria-label="Back to library">
          ← Library
        </Link>
        <h1 className="text-2xl font-bold text-white truncate">
          {document_?.title ?? 'Loading…'}
        </h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Chapter list */}
        <aside className="md:col-span-1">
          <ChapterList
            chapters={chapters}
            currentIndex={currentChapter}
            onSelect={handleChapterSelect}
          />
        </aside>

        {/* Player area */}
        <section className="md:col-span-3 space-y-6" aria-label="Audio player">
          {chapters.length === 0 ? (
            <div className="text-gray-400 text-center py-10">
              <p>Processing… check back shortly.</p>
              <ProgressBar value={null} label="Processing document" className="mt-4" />
            </div>
          ) : (
            <>
              <div className="bg-gray-800 rounded-xl p-6">
                <h2 className="text-lg font-semibold text-white mb-4">
                  {chapters[currentChapter]?.title ?? `Chapter ${currentChapter + 1}`}
                </h2>
                <AudioPlayer
                  src={null}  // Will be /chapters/{id}/audio in Milestone 3
                  onEnded={() => {
                    if (currentChapter < chapters.length - 1) {
                      handleChapterSelect(currentChapter + 1)
                    }
                  }}
                />
              </div>

              {/* Keyboard shortcut hint */}
              <div className="text-xs text-gray-500 flex flex-wrap gap-3">
                {['K: Play/Pause', 'J: -30s', 'L: +30s', 'N: Next', 'P: Prev', 'Space: Voice'].map(h => (
                  <span key={h} className="bg-gray-800 px-2 py-1 rounded font-mono">{h}</span>
                ))}
              </div>
            </>
          )}

          {/* Voice button */}
          <div className="flex justify-center">
            <VoiceButton onResult={handleVoiceResult} />
          </div>
        </section>
      </div>
    </main>
  )
}
