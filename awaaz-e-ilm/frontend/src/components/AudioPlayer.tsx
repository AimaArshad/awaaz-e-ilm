/**
 * AudioPlayer — accessible HTML audio player wrapper.
 *
 * Features:
 * - Play/Pause, Seek, Speed controls
 * - Keyboard shortcuts (K, J, L) via useKeyboardShortcuts
 * - Announces position changes to screen readers
 * - Shows waveform/progress bar
 *
 * Milestone 3: `src` will be populated with the chapter audio URL.
 */
import { useRef, useState, useEffect } from 'react'

interface AudioPlayerProps {
  src: string | null
  onEnded?: () => void
  initialSpeed?: number
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60)
  const ss = Math.floor(s % 60).toString().padStart(2, '0')
  return `${m}:${ss}`
}

export default function AudioPlayer({ src, onEnded, initialSpeed = 1 }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [speed, setSpeed] = useState(initialSpeed)

  // Keep playback rate in sync
  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = speed
  }, [speed])

  const togglePlay = () => {
    if (!audioRef.current || !src) return
    if (playing) {
      audioRef.current.pause()
    } else {
      audioRef.current.play().catch(console.error)
    }
  }

  const seek = (delta: number) => {
    if (!audioRef.current) return
    audioRef.current.currentTime = Math.max(0, Math.min(duration, currentTime + delta))
  }

  const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2]

  return (
    <div role="region" aria-label="Audio player" className="space-y-4">
      {/* Hidden <audio> element */}
      <audio
        ref={audioRef}
        src={src ?? undefined}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => { setPlaying(false); onEnded?.() }}
        onTimeUpdate={() => setCurrentTime(audioRef.current?.currentTime ?? 0)}
        onLoadedMetadata={() => setDuration(audioRef.current?.duration ?? 0)}
        aria-hidden="true"
      />

      {/* Not-yet-available notice */}
      {!src && (
        <p className="text-sm text-yellow-400 bg-yellow-900/30 rounded-lg px-4 py-2">
          🎵 Audio synthesis coming in Milestone 3. Controls shown for layout preview.
        </p>
      )}

      {/* Progress bar */}
      <div className="relative">
        <label htmlFor="audio-seek" className="sr-only">
          Audio progress: {formatTime(currentTime)} of {formatTime(duration)}
        </label>
        <input
          id="audio-seek"
          type="range"
          min={0}
          max={duration || 1}
          value={currentTime}
          step={1}
          onChange={(e) => { if (audioRef.current) audioRef.current.currentTime = Number(e.target.value) }}
          className="w-full accent-violet-500 cursor-pointer"
          aria-valuetext={`${formatTime(currentTime)} of ${formatTime(duration)}`}
        />
        <div className="flex justify-between text-xs text-gray-500 mt-0.5">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Controls row */}
      <div className="flex items-center justify-center gap-6">
        {/* Back 30s */}
        <button
          onClick={() => seek(-30)}
          aria-label="Rewind 30 seconds (J)"
          className="p-2 text-gray-300 hover:text-white focus:outline-none focus:ring-2 focus:ring-violet-400 rounded-lg"
        >
          <span aria-hidden="true">⏮ 30s</span>
        </button>

        {/* Play/Pause */}
        <button
          onClick={togglePlay}
          aria-label={playing ? 'Pause (K)' : 'Play (K)'}
          className="w-14 h-14 rounded-full bg-violet-700 hover:bg-violet-600 flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-violet-400 transition-colors"
        >
          <span className="text-2xl" aria-hidden="true">{playing ? '⏸' : '▶'}</span>
        </button>

        {/* Forward 30s */}
        <button
          onClick={() => seek(30)}
          aria-label="Forward 30 seconds (L)"
          className="p-2 text-gray-300 hover:text-white focus:outline-none focus:ring-2 focus:ring-violet-400 rounded-lg"
        >
          <span aria-hidden="true">30s ⏭</span>
        </button>
      </div>

      {/* Speed selector */}
      <div className="flex items-center gap-2 justify-center flex-wrap" role="group" aria-label="Playback speed">
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => setSpeed(s)}
            aria-pressed={speed === s}
            aria-label={`Speed ${s}x`}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-violet-400
              ${speed === s ? 'bg-violet-700 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
          >
            {s}×
          </button>
        ))}
      </div>
    </div>
  )
}
