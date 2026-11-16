/**
 * ws.ts — WebSocket client factories.
 *
 * createProgressSocket(documentId): WebSocket
 *   Connects to /ws/progress/{documentId} and streams Job progress events.
 *   Each message: { stage: string, progress: number, done: boolean }
 *
 * createVoiceSocket(): WebSocket
 *   Connects to /ws/voice for push-to-talk voice commands.
 *   Send binary audio frames; receive JSON intent responses.
 *
 * Usage:
 *   const ws = createProgressSocket(docId)
 *   ws.onmessage = (e) => { const data = JSON.parse(e.data); ... }
 *   ws.onclose = () => { ... }
 */

const WS_BASE = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000'

/**
 * Open a WebSocket for document processing progress updates.
 */
export function createProgressSocket(documentId: number): WebSocket {
  return new WebSocket(`${WS_BASE}/ws/progress/${documentId}`)
}

/**
 * Open a WebSocket for push-to-talk voice commands.
 */
export function createVoiceSocket(): WebSocket {
  return new WebSocket(`${WS_BASE}/ws/voice`)
}

/**
 * Subscribe to progress events until the job is done.
 *
 * @param documentId - Document ID to track
 * @param onProgress - Called with { stage, progress } on each update
 * @param onDone     - Called when progress reaches 1.0
 * @returns cleanup function (call to close the socket)
 */
export function subscribeProgress(
  documentId: number,
  onProgress: (data: { stage: string; progress: number; error?: string | null }) => void,
  onDone: () => void,
): () => void {
  const ws = createProgressSocket(documentId)

  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data as string)
      onProgress(data)
      if (data.done) {
        onDone()
        ws.close()
      }
    } catch { /* ignore */ }
  }

  ws.onerror = (err) => {
    console.error('Progress WebSocket error', err)
  }

  return () => ws.close()
}
