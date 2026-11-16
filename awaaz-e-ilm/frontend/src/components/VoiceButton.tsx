/**
 * VoiceButton — push-to-talk microphone button.
 *
 * Usage:
 * - Hold Space or click/touch to record
 * - Releases send audio to /ws/voice WebSocket
 * - Calls onResult({ intent, params }) with parsed voice command
 *
 * Accessibility:
 * - role="button" with aria-pressed for screen readers
 * - Announces listening/done states via aria-live
 *
 * Milestone 4: Connect to real WebSocket and stream PCM audio.
 */
import { useState, useEffect, useCallback, useRef } from 'react'

interface VoiceResult {
  intent: string
  params: Record<string, unknown>
  transcript?: string
}

interface VoiceButtonProps {
  onResult?: (result: VoiceResult) => void
  className?: string
}

export default function VoiceButton({ onResult, className = '' }: VoiceButtonProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [status, setStatus] = useState<'idle' | 'listening' | 'processing'>('idle')
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const startRecording = useCallback(async () => {
    if (isRecording) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        setStatus('processing')

        // TODO (Milestone 4): Send chunks to /ws/voice WebSocket
        // For now, return a stub result after 500 ms
        setTimeout(() => {
          onResult?.({
            intent: 'unknown',
            params: {},
            transcript: '(Voice command not yet wired — Milestone 4)',
          })
          setStatus('idle')
        }, 500)
      }

      recorder.start()
      mediaRef.current = recorder
      setIsRecording(true)
      setStatus('listening')
    } catch (err) {
      console.error('Microphone access denied', err)
      setStatus('idle')
    }
  }, [isRecording, onResult])

  const stopRecording = useCallback(() => {
    if (!isRecording || !mediaRef.current) return
    mediaRef.current.stop()
    mediaRef.current = null
    setIsRecording(false)
  }, [isRecording])

  // Space key → push-to-talk
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && e.target === document.body && !isRecording) {
        e.preventDefault()
        startRecording()
      }
    }
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space' && isRecording) {
        e.preventDefault()
        stopRecording()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
    }
  }, [isRecording, startRecording, stopRecording])

  const label = status === 'listening'
    ? 'Listening… release to send'
    : status === 'processing'
      ? 'Processing…'
      : 'Hold Space or click to speak a command'

  return (
    <div className={`flex flex-col items-center gap-3 ${className}`}>
      {/* ARIA live status */}
      <span aria-live="assertive" aria-atomic="true" className="sr-only">
        {status === 'listening' ? 'Listening for voice command' : ''}
      </span>

      <button
        type="button"
        role="button"
        aria-pressed={isRecording}
        aria-label={label}
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onTouchStart={(e) => { e.preventDefault(); startRecording() }}
        onTouchEnd={(e) => { e.preventDefault(); stopRecording() }}
        className={`w-20 h-20 rounded-full flex items-center justify-center transition-all focus:outline-none focus:ring-4 focus:ring-violet-400
          ${isRecording
            ? 'bg-red-600 hover:bg-red-500 scale-110 animate-pulse ring-4 ring-red-400'
            : status === 'processing'
              ? 'bg-yellow-600 scale-105'
              : 'bg-violet-700 hover:bg-violet-600'
          }`}
      >
        <span className="text-3xl" aria-hidden="true">
          {isRecording ? '🔴' : status === 'processing' ? '⏳' : '🎙️'}
        </span>
      </button>

      <p className="text-xs text-gray-400 text-center max-w-xs">{label}</p>
    </div>
  )
}
