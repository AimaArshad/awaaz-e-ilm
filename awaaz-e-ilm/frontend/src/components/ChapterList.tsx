/**
 * ChapterList — accessible chapter navigation sidebar.
 *
 * Shows all chapters with their processing status.
 * Highlights the currently playing chapter.
 * Fully keyboard navigable.
 */
import type { Chapter } from '../lib/api'

interface ChapterListProps {
  chapters: Chapter[]
  currentIndex: number
  onSelect: (index: number) => void
}

const STATUS_ICONS: Record<string, string> = {
  pending: '⏳',
  processing: '🔄',
  ready: '✅',
  failed: '❌',
}

export default function ChapterList({ chapters, currentIndex, onSelect }: ChapterListProps) {
  if (chapters.length === 0) {
    return (
      <div className="text-sm text-gray-500 text-center py-6">
        No chapters yet
      </div>
    )
  }

  return (
    <nav aria-label="Chapters">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3 px-1">
        Chapters ({chapters.length})
      </h2>
      <ul className="space-y-1" role="listbox" aria-label="Chapter list">
        {chapters.map((chapter, idx) => (
          <li
            key={chapter.id}
            role="option"
            aria-selected={idx === currentIndex}
          >
            <button
              onClick={() => onSelect(idx)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-violet-400
                ${idx === currentIndex
                  ? 'bg-violet-800 text-white font-medium'
                  : 'text-gray-300 hover:bg-gray-700'
                }`}
              aria-label={`Chapter ${idx + 1}: ${chapter.title}, status: ${chapter.status}`}
              aria-current={idx === currentIndex ? 'true' : undefined}
            >
              <span className="flex items-start gap-2">
                <span className="text-xs mt-0.5 shrink-0" aria-hidden="true">
                  {STATUS_ICONS[chapter.status] ?? '?'}
                </span>
                <span className="truncate">
                  {idx + 1}. {chapter.title}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
