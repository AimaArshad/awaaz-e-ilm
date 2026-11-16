/**
 * useAudioPlayer — HTMLAudioElement wrapper hook.
 *
 * Provides a clean React interface over HTMLAudioElement with:
 * - play / pause / seek / setSpeed
 * - currentTime and duration state
 * - onEnded callback
 *
 * Usage:
 *   const { playerRef, playing, currentTime, duration, play, pause, seek, setSpeed } = useAudioPlayer()
 *   <audio ref={playerRef} src={src} />
 */
import { useRef, useState, useCallback } from 'react'

export function useAudioPlayer() {
  const playerRef = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [speed, setSpeedState] = useState(1)

  const play = useCallback(() => {
    playerRef.current?.play().catch(console.error)
  }, [])

  const pause = useCallback(() => {
    playerRef.current?.pause()
  }, [])

  const togglePlay = useCallback(() => {
    if (playing) pause()
    else play()
  }, [playing, play, pause])

  const seek = useCallback((seconds: number) => {
    if (!playerRef.current) return
    const el = playerRef.current
    el.currentTime = Math.max(0, Math.min(el.duration || 0, seconds))
  }, [])

  const seekDelta = useCallback((delta: number) => {
    if (!playerRef.current) return
    seek(playerRef.current.currentTime + delta)
  }, [seek])

  const setSpeed = useCallback((s: number) => {
    setSpeedState(s)
    if (playerRef.current) playerRef.current.playbackRate = s
  }, [])

  const handlers = {
    onPlay: () => setPlaying(true),
    onPause: () => setPlaying(false),
    onEnded: () => setPlaying(false),
    onTimeUpdate: () => setCurrentTime(playerRef.current?.currentTime ?? 0),
    onLoadedMetadata: () => setDuration(playerRef.current?.duration ?? 0),
  }

  return {
    playerRef,
    playing,
    currentTime,
    duration,
    speed,
    play,
    pause,
    togglePlay,
    seek,
    seekDelta,
    setSpeed,
    handlers,
  }
}
