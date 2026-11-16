/**
 * useVoiceCommands — push-to-talk voice command hook.
 *
 * Connects to the /ws/voice WebSocket and streams MediaRecorder audio.
 * Returns the latest parsed intent result.
 *
 * Usage:
 *   const { isRecording, start, stop, lastResult } = useVoiceCommands()
 *
 * Milestone 4: Replace stub with real WebSocket + PCM audio streaming.
 */
import { useState, useCallback, useRef } from 'react'
import { createVoiceSocket } from '../lib/ws'

export interface VoiceResult {
  intent: string
  params: Record<string, unknown>
  transcript: string
}

export function useVoiceCommands() {
  const [isRecording, setIsRecording] = useState(false)
  const [lastResult, setLastResult] = useState<VoiceResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const start = useCallback(async () => {
    if (isRecording) return
    setError(null)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      // Open WebSocket
      const ws = createVoiceSocket()
      wsRef.current = ws

      ws.onmessage = (e) => {
        try {
          const result: VoiceResult = JSON.parse(e.data)
          setLastResult(result)
        } catch {
          // ignore parse errors
        }
      }

      ws.onerror = () => setError('WebSocket error — is the backend running?')

      // Start MediaRecorder
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      recorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          ws.send(e.data)
        }
      }

      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        ws.send(JSON.stringify({ action: 'stop' }))
      }

      recorder.start(100) // 100ms chunks
      setIsRecording(true)
    } catch (err) {
      setError(`Microphone access denied: ${(err as Error).message}`)
    }
  }, [isRecording])

  const stop = useCallback(() => {
    recorderRef.current?.stop()
    recorderRef.current = null
    setIsRecording(false)
  }, [])

  return { isRecording, start, stop, lastResult, error }
}
