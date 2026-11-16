/**
 * Transcript — sentence-highlighted scrolling transcript.
 *
 * Highlights the sentence currently being spoken based on `activeSentenceIndex`.
 * Automatically scrolls the active sentence into view.
 * Screen readers get aria-live="polite" for the active sentence.
 *
 * Milestone 3: Connect activeSentenceIndex to the word-timing data
 * from GET /chapters/{id}/timing.
 */
import { useEffect, useRef } from 'react'

interface TranscriptProps {
  sentences: string[]
  activeSentenceIndex: number
  lang?: 'en' | 'ur'
}

export default function Transcript({ sentences, activeSentenceIndex, lang = 'en' }: TranscriptProps) {
  const activeRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [activeSentenceIndex])

  if (sentences.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic py-4 text-center">
        Transcript not yet available.
      </div>
    )
  }

  return (
    <div
      role="region"
      aria-label="Chapter transcript"
      lang={lang}
      dir={lang === 'ur' ? 'rtl' : 'ltr'}
      className="max-h-64 overflow-y-auto space-y-2 pr-2 text-sm leading-relaxed"
    >
      {/* Active sentence announced to screen readers */}
      <span aria-live="polite" aria-atomic="true" className="sr-only">
        {sentences[activeSentenceIndex] ?? ''}
      </span>

      {sentences.map((sentence, idx) => (
        <p
          key={idx}
          ref={idx === activeSentenceIndex ? activeRef : undefined}
          aria-current={idx === activeSentenceIndex ? 'true' : undefined}
          className={`px-3 py-1.5 rounded-lg transition-colors
            ${idx === activeSentenceIndex
              ? 'bg-violet-800 text-white font-medium'
              : idx < activeSentenceIndex
                ? 'text-gray-500'
                : 'text-gray-200'
            }`}
        >
          {sentence}
        </p>
      ))}
    </div>
  )
}
